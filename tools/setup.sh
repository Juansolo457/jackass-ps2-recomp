#!/bin/sh
# Set up everything tools/build.sh needs that isn't in the repository (docs/SETUP.md):
#   1. third_party/PS2Recomp: ran-j/PS2Recomp at the pinned commit in third_party/PS2Recomp.commit
#      (the first run, with no pin yet, clones the default branch and writes the pin), with this
#      project's patches from tools/patches/ applied, then built;
#   2. a check that the programs the pipeline needs are on PATH: git, python3, clang/clang++,
#      cmake, ninja, chdman (optional: only for CHD dumps), glslc or glslangValidator.
# Nothing is downloaded other than the git clone; the Linux distribution's packages provide the
# rest (Debian/Ubuntu: clang cmake ninja-build mame-tools libvulkan-dev glslc libsdl3-dev;
# Arch/SteamOS: clang cmake ninja mame-tools vulkan-headers shaderc sdl3).
#   tools/setup.sh            # all of it (skips what is there already)
#   tools/setup.sh --force    # re-clone PS2Recomp
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
third=$root/third_party
pinfile=$third/PS2Recomp.commit
src=$third/PS2Recomp
upstream=https://github.com/ran-j/PS2Recomp
# Default pin: the commit KIexster/god-of-war-recomp builds on (docs/REFERENCES.md); Waffle565's
# runtime is a patch over it. Override with PS2RECOMP_PIN=<sha> on the first run.
default_pin=${PS2RECOMP_PIN:-c5a9d02573410a2085a4b4b831b0b68ba3515440}
# KIexster's patch stack (GPL-3.0): fetched read-only into third_party/god-of-war-recomp for the
# runtime patch and its Linux fixes. Pinned by third_party/god-of-war-recomp.commit (first run
# records HEAD).
gow_repo=https://github.com/KIexster/god-of-war-recomp
gow=$third/god-of-war-recomp
gowpin=$third/god-of-war-recomp.commit
force=0
[ "${1:-}" = "--force" ] && force=1

need() { command -v "$1" >/dev/null 2>&1 || { echo "setup: $1 is not on PATH ($2)" >&2; missing=1; }; }
missing=0
need git "install git"
need python3 "install python3"
need cmake "install cmake"
need ninja "install ninja-build / ninja"
if ! command -v clang++ >/dev/null 2>&1 && ! command -v g++ >/dev/null 2>&1; then
  echo "setup: no C++ compiler (install clang)" >&2; missing=1
fi
command -v chdman >/dev/null 2>&1 || echo "setup: chdman not found: only needed for CHD dumps (mame-tools)"
if ! command -v glslc >/dev/null 2>&1 && ! command -v glslangValidator >/dev/null 2>&1; then
  echo "setup: no GLSL compiler yet: needed from Layer 7 (shaderc / glslang)"
fi
[ "$missing" = 0 ] || exit 1

mkdir -p "$third"
if [ "$force" = 1 ] && [ -d "$src" ]; then rm -rf "$src"; fi
if [ ! -d "$src/.git" ]; then
  echo "setup: cloning $upstream"
  git clone --recurse-submodules "$upstream" "$src"
fi
if [ -f "$pinfile" ]; then
  pin=$(tr -d ' \n\r' < "$pinfile")
  git -C "$src" fetch --quiet origin
  git -C "$src" checkout --quiet "$pin"
  git -C "$src" submodule update --init --recursive --quiet
else
  pin=$default_pin
  git -C "$src" checkout --quiet "$pin"
  git -C "$src" submodule update --init --recursive --quiet
  printf '%s\n' "$pin" > "$pinfile"
  echo "setup: pinned PS2Recomp at $pin (third_party/PS2Recomp.commit)"
fi
echo "setup: PS2Recomp $pin"
if ! grep -q 'GNU GENERAL PUBLIC LICENSE' "$src/LICENSE" 2>/dev/null; then
  echo "setup: WARNING: PS2Recomp's LICENSE at $pin is not the GPL text NOTICE expects; check LICENSES/PROVENANCE.md" >&2
fi

# KIexster's repo, for the Waffle565 runtime patch and the Linux/GCC fixes (read-only reference;
# which of its patches we apply, and in what order, is decided in tools/patches/ORDER once
# Layer 1 starts).
if [ ! -d "$gow/.git" ]; then
  echo "setup: cloning $gow_repo (reference, GPL-3.0)"
  git clone --quiet "$gow_repo" "$gow"
fi
if [ -f "$gowpin" ]; then
  git -C "$gow" fetch --quiet origin && git -C "$gow" checkout --quiet "$(tr -d ' \n\r' < "$gowpin")"
else
  git -C "$gow" rev-parse HEAD > "$gowpin"
  echo "setup: pinned god-of-war-recomp at $(cat "$gowpin")"
fi

# Project patches, in name order; each must apply cleanly to the pin.
for p in "$root"/tools/patches/*.patch; do
  [ -e "$p" ] || break
  if git -C "$src" apply --check "$p" 2>/dev/null; then
    git -C "$src" apply "$p"; echo "setup: applied $(basename "$p")"
  elif git -C "$src" apply --reverse --check "$p" 2>/dev/null; then
    echo "setup: already applied $(basename "$p")"
  else
    echo "setup: $(basename "$p") does not apply to $pin" >&2; exit 1
  fi
done

# Build PS2Recomp's tools (analyzer, recompiler, runtime library).
jobs=${JOBS:-$(nproc 2>/dev/null || echo 4)}
cmake -S "$src" -B "$src/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  ${CXX:+-DCMAKE_CXX_COMPILER="$CXX"} ${CC:+-DCMAKE_C_COMPILER="$CC"}
cmake --build "$src/build" -j "$jobs"
echo "setup: done. Next: tools/extract.sh /path/to/Jackass.chd"
