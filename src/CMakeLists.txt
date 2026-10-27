# The game: the recompiled code (generated/, from tools/generate.sh) plus our host code, on the runtime from
# engine/runtime. Modelled on the Urban Reign port's src/CMakeLists.txt (GPL-3.0); the same flags for the generated
# code (Clang/GCC: no warnings, no debug info by default; register_functions.cpp at -O0, its one huge table).
set(JA_ARCH "SSE41" CACHE STRING "Instruction set of the generated code: SSE41 (default) or AVX2")
set_property(CACHE JA_ARCH PROPERTY STRINGS SSE41 AVX2)
if(JA_ARCH STREQUAL "AVX2")
    set(JA_ARCH_FLAG $<IF:$<BOOL:${MSVC}>,/arch:AVX2,-mavx2>)
else()
    set(JA_ARCH_FLAG "")
endif()
option(JA_GENERATED_DEBUG_INFO "Clang/GCC: debug info for the generated code" OFF)
set(JA_GENERATED_FLAGS -w ${JA_ARCH_FLAG})
if(NOT JA_GENERATED_DEBUG_INFO AND NOT MSVC)
    list(APPEND JA_GENERATED_FLAGS -g0)
endif()

set(JA_GENERATED_DIR "${CMAKE_SOURCE_DIR}/generated")
set(JA_RUNTIME_INCLUDE "${JA_RUNTIME_ROOT}/runtime/ps2xRuntime/include")
set(JA_RUNTIME_LIB "${JA_RUNTIME_ROOT}/runtime/ps2xRuntime/src/lib")

if(NOT EXISTS "${JA_GENERATED_DIR}/register_functions.cpp")
    message(FATAL_ERROR "Recompiled game code not found in ${JA_GENERATED_DIR}: run tools/generate.sh first.")
endif()
file(GLOB JA_GENERATED_SOURCES CONFIGURE_DEPENDS "${JA_GENERATED_DIR}/*.cpp")

# Huge generated files (one function of thousands of instructions) get their own library and job pool so a few of
# them cannot take every core's memory at once.
set(JA_HUGE_SOURCE_BYTES 900000 CACHE STRING "Generated files larger than this go into the huge-sources library")
set(JA_HUGE_SOURCES "")
foreach(source IN LISTS JA_GENERATED_SOURCES)
    file(SIZE "${source}" sourceBytes)
    if(sourceBytes GREATER JA_HUGE_SOURCE_BYTES AND NOT source MATCHES "register_functions\\.cpp$")
        list(APPEND JA_HUGE_SOURCES "${source}")
    endif()
endforeach()
if(JA_HUGE_SOURCES)
    list(REMOVE_ITEM JA_GENERATED_SOURCES ${JA_HUGE_SOURCES})
endif()

add_library(ja_game_code_huge STATIC ${JA_HUGE_SOURCES} "${CMAKE_CURRENT_SOURCE_DIR}/jackass/empty.cpp")
target_include_directories(ja_game_code_huge PUBLIC "${JA_GENERATED_DIR}")
target_link_libraries(ja_game_code_huge PUBLIC ps2_runtime)
set(JA_HUGE_JOBS 2 CACHE STRING "Concurrent compiles of the huge generated sources (Ninja)")
set_property(GLOBAL APPEND PROPERTY JOB_POOLS ja_huge=${JA_HUGE_JOBS})
set_property(TARGET ja_game_code_huge PROPERTY JOB_POOL_COMPILE ja_huge)
target_compile_options(ja_game_code_huge PRIVATE ${JA_GENERATED_FLAGS})

add_library(ja_game_code STATIC ${JA_GENERATED_SOURCES})
target_link_libraries(ja_game_code PUBLIC ja_game_code_huge ps2_runtime)
target_include_directories(ja_game_code PUBLIC "${JA_GENERATED_DIR}")
set_target_properties(ja_game_code PROPERTIES UNITY_BUILD OFF)
target_precompile_headers(ja_game_code PRIVATE
    "${JA_RUNTIME_INCLUDE}/ps2_runtime_macros.h"
    "${JA_RUNTIME_INCLUDE}/ps2_runtime.h"
    "${JA_GENERATED_DIR}/ps2_recompiled_functions.h"
    "${JA_GENERATED_DIR}/ps2_recompiled_stubs.h"
    "${JA_RUNTIME_INCLUDE}/ps2_syscalls.h"
    "${JA_RUNTIME_INCLUDE}/ps2_stubs.h"
)
target_compile_options(ja_game_code PRIVATE ${JA_GENERATED_FLAGS})
set_source_files_properties("${JA_GENERATED_DIR}/register_functions.cpp" PROPERTIES
    COMPILE_OPTIONS "-O0" SKIP_PRECOMPILE_HEADERS ON)

set(JA_HOST_SOURCES
    main.cpp
    jackass/call_profile.cpp
    jackass/function_hooks.cpp
    jackass/game_disc.cpp
    jackass/hang_dump.cpp
    jackass/hle_bindings.cpp
    jackass/log.cpp
    jackass/ret_trace.cpp
    jackass/sha256.cpp
)
add_executable(jackass ${JA_HOST_SOURCES})
target_include_directories(jackass PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${JA_GENERATED_DIR}")
target_link_libraries(jackass PRIVATE ja_game_code ps2_runtime)
target_compile_definitions(jackass PRIVATE JA_ARCH_NAME="${JA_ARCH}")
if(MSVC)
    target_compile_options(jackass PRIVATE /fp:precise /W3 /utf-8)
    target_link_options(jackass PRIVATE /FORCE:MULTIPLE /STACK:16777216)
else()
    find_package(Threads REQUIRED)
    target_link_options(jackass PRIVATE -rdynamic)
    target_link_libraries(jackass PRIVATE Threads::Threads ${CMAKE_DL_LIBS})
endif()

if(JA_DEBUG_UI AND TARGET rlImGui)
    target_sources(jackass PRIVATE "${JA_RUNTIME_LIB}/ps2_debug_panel.cpp")
    target_include_directories(jackass PRIVATE "${JA_RUNTIME_LIB}")
    target_link_libraries(jackass PRIVATE rlImGui imgui)
    target_compile_definitions(jackass PRIVATE PS2X_ENABLE_DEBUG_UI=1)
endif()
if(TARGET pcsx2gs)
    add_dependencies(jackass pcsx2gs)
    target_link_libraries(ps2_runtime PRIVATE pcsx2gs_api)
    target_link_libraries(jackass PRIVATE pcsx2gs_api)
endif()

# VU1 microcode compiled ahead of time: capture with PS2X_VU1_CAPTURE=<dir>, run the runtime's vu1_recomp
# (-DJA_BUILD_TOOLS=ON) into generated/vu1; images not compiled stay interpreted.
file(GLOB JA_VU1_SOURCES CONFIGURE_DEPENDS "${JA_GENERATED_DIR}/vu1/*.cpp")
if(JA_VU1_SOURCES)
    add_library(ja_vu1_code STATIC ${JA_VU1_SOURCES})
    target_include_directories(ja_vu1_code PRIVATE "${JA_RUNTIME_LIB}/vu")
    target_link_libraries(ja_vu1_code PUBLIC ps2_runtime)
    target_link_libraries(jackass PRIVATE ja_vu1_code)
    target_compile_definitions(jackass PRIVATE JA_HAS_VU1_PROGRAMS=1)
    target_compile_options(ja_vu1_code PRIVATE ${JA_GENERATED_FLAGS})
endif()

set_target_properties(jackass PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
