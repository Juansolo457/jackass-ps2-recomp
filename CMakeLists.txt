cmake_minimum_required(VERSION 3.21)
# Jackass PS2 Recompiled: the game's recompiled code plus our host code (src/), on the PS2Recomp runtime and
# PCSX2's GS from the Urban Reign PC port's checkout in engine/runtime/ (tools/setup.sh). Modelled on that port's
# top-level CMakeLists.txt (GPL-3.0); the flags below are its "MSVC code model" for Clang/GCC, which the
# recompiled code and the runtime's SSE4.1 intrinsics assume.
project(JackassPS2 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(JA_RUNTIME_ROOT "${CMAKE_SOURCE_DIR}/engine/runtime" CACHE PATH "The Urban Reign checkout (engine/runtime.toml)")
if(NOT EXISTS "${JA_RUNTIME_ROOT}/runtime/CMakeLists.txt")
    message(FATAL_ERROR "engine/runtime is missing: run tools/setup.sh first (engine/runtime.toml).")
endif()

if(NOT MSVC)
    if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
        set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
    endif()
    # SSE4.1 intrinsics need the ISA enabled; the generated code assumes no type-based aliasing, wrapping signed
    # arithmetic and no FMA contraction (/fp:precise).
    add_compile_options(-msse4.1 -fno-strict-aliasing -fwrapv -ffp-contract=off)
    set(CMAKE_BUILD_RPATH_USE_ORIGIN ON)
    set(CMAKE_BUILD_RPATH "$ORIGIN")
    set(CMAKE_INSTALL_RPATH "$ORIGIN")
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    # raylib's GLFW as X11 only: PCSX2's GS renders into an X11 child window (XWayland on Wayland).
    set(GLFW_BUILD_WAYLAND OFF CACHE BOOL "" FORCE)
    set(GLFW_BUILD_X11 ON CACHE BOOL "" FORCE)
endif()

option(JA_BUILD_RECOMP "Build ps2_recomp from the runtime's ps2xRecomp" ON)
option(JA_BUILD_TOOLS "Build the runtime's offline tools (vu1_recomp, gs_replay, vu0_audit)" OFF)
option(JA_DEBUG_UI "Build the ImGui runtime debugger into the game (F1)" ON)
option(JA_PCSX2_GS "Build PCSX2's GS (libpcsx2gs.so / pcsx2gs.dll)" ON)
# The runtime's own option names (Urban Reign's CMake reads URBAN_*; map ours onto them).
set(URBAN_BUILD_RECOMP ${JA_BUILD_RECOMP} CACHE BOOL "" FORCE)
set(URBAN_BUILD_TOOLS ${JA_BUILD_TOOLS} CACHE BOOL "" FORCE)
set(PS2X_ENABLE_DEBUG_UI ${JA_DEBUG_UI} CACHE BOOL "" FORCE)
set(PS2X_ENABLE_FFMPEG OFF CACHE BOOL "" FORCE)          # movies go through the emulated IPU
set(PS2X_ENABLE_AGRESSIVE_LOGS OFF CACHE BOOL "" FORCE)
set(PS2X_ENABLE_SCCACHE OFF CACHE BOOL "" FORCE)

# The runtime (EE/IOP/VU/GS emulation, recompiler, offline tools) and PCSX2's GS, from the checkout. Their
# CMake files may still refer to paths relative to their own top level (Urban Reign's src/ and generated/);
# anything that does is fixed with a patch in engine/patches/, never by editing engine/runtime in place.
add_subdirectory("${JA_RUNTIME_ROOT}/runtime" "${CMAKE_BINARY_DIR}/runtime" EXCLUDE_FROM_ALL)
if(JA_PCSX2_GS AND (WIN32 OR CMAKE_SYSTEM_NAME STREQUAL "Linux"))
    add_subdirectory("${JA_RUNTIME_ROOT}/thirdparty/pcsx2-gs" "${CMAKE_BINARY_DIR}/pcsx2-gs" EXCLUDE_FROM_ALL)
endif()

# Our port: src/CMakeLists.txt builds the game (recompiled code in generated/ + src/) once Layer 2 produces it.
if(EXISTS "${CMAKE_SOURCE_DIR}/src/CMakeLists.txt")
    add_subdirectory(src)
else()
    message(STATUS "src/CMakeLists.txt not written yet: only the recompiler and the GS are buildable (tools/setup.sh)")
endif()
