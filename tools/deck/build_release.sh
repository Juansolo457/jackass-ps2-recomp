#!/bin/bash
# Builds the Linux release binaries inside the Steam Runtime 3 "sniper" SDK container, so they need only glibc 2.31
# and the libraries every desktop and SteamOS has (X11, OpenGL, Vulkan): g++ 14 with a static libstdc++/libgcc,
# shaderc built from source next to them. Adapted from the Urban Reign port's tools/linux/build_release.sh
# (GPL-3.0-or-later, like this file); run through tools/deck/release.sh, which starts the container with the
# repository at /src and the out-of-tree build root at the same path it has on the host.
# Output: $OUT/build/bin (jackass, libpcsx2gs.so, libSDL3.so.0, resources/) and $OUT/deps (libshaderc, libpng).
set -euo pipefail

SRC=/src
OUT="${JA_RELEASE_OUT:?set by tools/deck/release.sh}"
JOBS="${JOBS:-$(nproc)}"
export CC=gcc-14 CXX=g++-14
STATIC_RUNTIME="-static-libstdc++ -static-libgcc"

# --- shaderc, the versions PCSX2 builds with (as the Urban Reign port pins them) ---
SHADERC=2026.2
SHADERC_GLSLANG=275822a6261ee689aadb1da5f09a0ec2f058685c
SHADERC_SPIRVHEADERS=58006c901d1d5c37dece6b6610e9af87fa951375
SHADERC_SPIRVTOOLS=6337eb62cadd7d124ac6789bf39c0f71148f0a73
DOWNLOADS="$OUT/downloads"
SHADERC_DIR="$OUT/deps/shaderc"

fetch() { # url file sha256
    if [ ! -f "$DOWNLOADS/$2" ]; then
        curl -fL --retry 3 -o "$DOWNLOADS/$2.part" "$1"
        mv "$DOWNLOADS/$2.part" "$DOWNLOADS/$2"
    fi
    echo "$3  $DOWNLOADS/$2" | sha256sum -c -
}

if [ ! -f "$SHADERC_DIR/lib/libshaderc_shared.so.1" ]; then
    mkdir -p "$DOWNLOADS" "$OUT/deps"
    fetch "https://github.com/google/shaderc/archive/v$SHADERC.tar.gz" "shaderc-$SHADERC.tar.gz" \
        f924178e75e3293082481b25ed64d5e48a795b479dac3bd3c83d23070855df42
    fetch "https://github.com/KhronosGroup/glslang/archive/$SHADERC_GLSLANG.tar.gz" "glslang-$SHADERC_GLSLANG.tar.gz" \
        971848a1cc639ce8dc244e778b17efe0f690e32ac398a75e31d1c67ad06d3e0a
    fetch "https://github.com/KhronosGroup/SPIRV-Headers/archive/$SHADERC_SPIRVHEADERS.tar.gz" \
        "spirv-headers-$SHADERC_SPIRVHEADERS.tar.gz" a6cb1b300bb8171795e116457e858e555334749f9cacaed8068ae0ef8681110c
    fetch "https://github.com/KhronosGroup/SPIRV-Tools/archive/$SHADERC_SPIRVTOOLS.tar.gz" \
        "spirv-tools-$SHADERC_SPIRVTOOLS.tar.gz" e156be0bd81c8812f1bff8e520422bfa9df61b3045587b9eb483185f1074a7b2
    WORK="$OUT/deps/shaderc-src"
    rm -rf "$WORK"
    mkdir -p "$WORK"
    tar xf "$DOWNLOADS/shaderc-$SHADERC.tar.gz" -C "$WORK" --strip-components=1
    for dep in "glslang:glslang-$SHADERC_GLSLANG" "spirv-headers:spirv-headers-$SHADERC_SPIRVHEADERS" \
               "spirv-tools:spirv-tools-$SHADERC_SPIRVTOOLS"; do
        mkdir -p "$WORK/third_party/${dep%%:*}"
        tar xf "$DOWNLOADS/${dep#*:}.tar.gz" -C "$WORK/third_party/${dep%%:*}" --strip-components=1
    done
    cmake -S "$WORK" -B "$WORK/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$SHADERC_DIR" \
        -DCMAKE_INSTALL_LIBDIR=lib -DSHADERC_SKIP_TESTS=ON -DSHADERC_SKIP_EXAMPLES=ON -DSHADERC_SKIP_COPYRIGHT_CHECK=ON \
        -DCMAKE_SHARED_LINKER_FLAGS="$STATIC_RUNTIME" -DCMAKE_CXX_VISIBILITY_PRESET=hidden
    cmake --build "$WORK/build" --parallel "$JOBS" --target shaderc_shared
    mkdir -p "$SHADERC_DIR/lib" "$SHADERC_DIR/include"
    cp -a "$WORK/libshaderc/include/shaderc" "$SHADERC_DIR/include/"
    cp -a "$WORK"/build/libshaderc/libshaderc_shared.so* "$SHADERC_DIR/lib/"
    rm -rf "$WORK"
fi

# --- the game: the same CMake as the development build, with g++ 14 and the static C++ runtime ---
cmake -S "$SRC" -B "$OUT/build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DSHADERC_INCLUDE_DIR="$SHADERC_DIR/include" -DJA_DEBUG_UI=OFF \
    -DCMAKE_EXE_LINKER_FLAGS="$STATIC_RUNTIME" -DCMAKE_SHARED_LINKER_FLAGS="$STATIC_RUNTIME"
cmake --build "$OUT/build" --parallel "$JOBS" --target jackass pcsx2gs

# libpng goes with the game too (PCSX2's GS links it), found next to libpcsx2gs.so (RPATH $ORIGIN).
mkdir -p "$OUT/deps/libpng"
cp -L /usr/lib/x86_64-linux-gnu/libpng16.so.16 "$OUT/deps/libpng/libpng16.so.16"
echo "release build: done -> $OUT/build/bin"
