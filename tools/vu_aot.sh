#!/bin/bash
# Compile Jackass's VU microprograms ahead of time (about 9x faster gameplay than the runtime's VU interpreter).
#
#   1. Capture the images while playing (menus + a stunt or two; images seen later are captured then):
#        PS2X_VU1_CAPTURE=$HOME/jackass-out/vucapture PS2X_VU0_CAPTURE=$HOME/jackass-out/vucapture tools/launch.sh
#   2. tools/vu_aot.sh [capture-dir]      -> generated/vu1 (git-ignored: it is derived from the game's code)
#   3. tools/build.sh                     (src/CMakeLists.txt compiles generated/vu1; src/main.cpp registers it)
#
# vu1_recomp's fast defaults (raw loads, fast FMACs, dead-flag and self-loop shortcuts) are Urban Reign's and
# miscompile four of Jackass's programs (PS2X_VU1_VERIFY=obs: ~9% of their runs differ; the character vanished in
# stunts). The conservative settings below matched the interpreter on all 18 images over ~1.1M runs, at the same
# speed (97% of full speed on the PC). Check new captures with PS2X_VU1_VERIFY=obs PS2X_VU0_VERIFY=obs.
# Images not compiled run interpreted; PS2X_VU1_RECOMP=0 / PS2X_VU0_RECOMP=0 turn the compiled code off.
set -e
root=$(cd "$(dirname "$0")/.." && pwd)
capture=${1:-$HOME/jackass-out/vucapture}
build=${JA_BUILD_DIR:-$root/build/linux}
tool=$(find "$build" -name vu1_recomp -type f -perm -u+x 2>/dev/null | head -1)
if [ -z "$tool" ]; then
  cmake -S "$root" -B "$build" -DJA_BUILD_TOOLS=ON > /dev/null
  cmake --build "$build" --target vu1_recomp
  tool=$(find "$build" -name vu1_recomp -type f -perm -u+x | head -1)
fi
mkdir -p "$root/generated/vu1"
env VU1_RECOMP_EXACT_FMAC=1 VU1_RECOMP_NORM_LOADS=1 VU1_RECOMP_NO_DEAD_FLAGS=1 VU1_RECOMP_NO_SELF_LOOPS=1 \
    VU1_RECOMP_VU0_EXACT=1 VU1_RECOMP_ALL_READY=1 VU1_RECOMP_STICKY=1 \
    "$tool" "$capture" "$root/generated/vu1"
echo "vu_aot: $(ls "$capture"/vu1_*.bin | wc -l) images -> generated/vu1; now tools/build.sh"
