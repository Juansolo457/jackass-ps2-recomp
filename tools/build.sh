#!/bin/sh
# Build the game: cmake --build build/linux (the recompiled code in generated/ + src/, the runtime, libpcsx2gs.so).
#   tools/build.sh [-j N] [target]     # default target: jackass; JOBS=N also works
# Needs tools/setup.sh (configure, runtime) and tools/generate.sh (generated/) first. The first build compiles
# ~14k generated files: minutes with Clang on many cores.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=$root/build/linux
jobs=${JOBS:-$(nproc 2>/dev/null || echo 4)}
target=jackass
while [ $# -gt 0 ]; do
  case "$1" in
    -j) jobs=$2; shift ;;
    -j*) jobs=${1#-j} ;;
    *) target=$1 ;;
  esac
  shift
done
[ -f "$build/CMakeCache.txt" ] || { echo "build: not configured: run tools/setup.sh" >&2; exit 1; }
[ -f "$root/generated/register_functions.cpp" ] || { echo "build: no generated code: run tools/generate.sh" >&2; exit 1; }
if pgrep -x jackass >/dev/null 2>&1; then echo "build: the game is running; close it first (the link would fail)" >&2; exit 1; fi
# generated/ changed since configure? CONFIGURE_DEPENDS globs re-run CMake by themselves; src/CMakeLists.txt is new
# when the first game build happens, so configure again when the jackass target is unknown.
if ! cmake --build "$build" --target help 2>/dev/null | grep -q '^jackass:'; then
  cmake -S "$root" -B "$build"
fi
cmake --build "$build" --target "$target" -- -j "$jobs"
echo "build: done -> $build/bin/$target"
