#!/bin/sh
# Set up everything the build needs that isn't in the repository (docs/SETUP.md):
#   1. engine/runtime/: the Urban Reign PC port's checkout at the commit pinned in engine/runtime.toml, with this
#      project's patches (engine/patches/*.patch, in name order) applied. It carries PS2Recomp with that port's
#      runtime changes and PCSX2's GS as a library (see engine/runtime.toml for what is inside).
#   2. a check that the programs the pipeline needs are on PATH (clang, cmake, ninja, python3, git; chdman only
#      for CHD dumps). Debian/Ubuntu packages: see docs/SETUP.md (tools/linux/install_deps.sh in the checkout lists
#      what Urban Reign's Linux build wants: X11 headers, libgl, libvulkan-dev, libshaderc-dev, libpng-dev).
#   3. the recompiler (ps2_recomp) and PCSX2's GS (libpcsx2gs.so) built from that checkout through this repo's
#      CMakeLists.txt into build/linux. Nothing game-derived is touched here.
# Nothing is downloaded other than the git clone (and the runtime's own FetchContent dependencies at configure:
# raylib, SDL3, fmt, toml11, ...).
#   tools/setup.sh            # all of it (skips what is there already)
#   tools/setup.sh --force    # re-clone the runtime
#   JOBS=14 tools/setup.sh    # parallel jobs (default: nproc)
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
engine=$root/engine
rt=$engine/runtime
build=$root/build/linux
force=0
[ "${1:-}" = "--force" ] && force=1

toml_value() { sed -n "s/^$1 *= *\"\([^\"]*\)\".*/\1/p" "$engine/runtime.toml" | head -n 1; }
repo=$(toml_value repository)
pin=$(toml_value commit)
[ -n "$repo" ] && [ -n "$pin" ] || { echo "setup: engine/runtime.toml has no repository/commit" >&2; exit 1; }

# --- 1. tools --------------------------------------------------------------------------------------------------
missing=0
need() { command -v "$1" >/dev/null 2>&1 || { echo "setup: $1 is not on PATH ($2)" >&2; missing=1; }; }
need git "apt install git"
need python3 "apt install python3 (3.11+ for tools/profile.py)"
need cmake "apt install cmake"
need ninja "apt install ninja-build"
need clang++ "apt install clang lld"
need pkg-config "apt install pkg-config"
command -v chdman >/dev/null 2>&1 || echo "setup: chdman not found: only needed for CHD dumps (mame-tools)"
command -v glslc >/dev/null 2>&1 || echo "setup: glslc not found (optional; PCSX2's GS compiles its shaders with shaderc's shared library at run time)"
pkg-config --exists vulkan 2>/dev/null || echo "setup: libvulkan-dev not found: needed for libpcsx2gs.so"
[ "$missing" = 0 ] || exit 1

# --- 2. the runtime checkout ------------------------------------------------------------------------------------
if [ "$force" = 1 ] && [ -d "$rt" ]; then rm -rf "$rt"; fi
if [ ! -d "$rt/.git" ]; then
  echo "setup: cloning $repo"
  git clone --quiet "$repo" "$rt"
fi
if [ "$(git -C "$rt" rev-parse HEAD)" != "$pin" ]; then
  git -C "$rt" fetch --quiet origin
  git -C "$rt" checkout --quiet --force "$pin"
  git -C "$rt" clean -fdq
fi
git -C "$rt" submodule update --init --recursive --quiet 2>/dev/null || true
echo "setup: engine/runtime at $pin"
grep -q 'GNU GENERAL PUBLIC LICENSE' "$rt/LICENSE" 2>/dev/null || \
  echo "setup: WARNING: the runtime's LICENSE is not the GPL text NOTICE expects; check LICENSES/PROVENANCE.md" >&2

# Our patches, in name order; each must apply cleanly to the pin (git apply skips the header lines).
# A fresh checkout is clean, so an already-applied patch is detected with --reverse --check.
for p in "$engine"/patches/*.patch; do
  [ -e "$p" ] || break
  if git -C "$rt" apply --check --ignore-whitespace "$p" 2>/dev/null; then
    git -C "$rt" apply --ignore-whitespace "$p"; echo "setup: applied $(basename "$p")"
  elif git -C "$rt" apply --reverse --check --ignore-whitespace "$p" 2>/dev/null; then
    echo "setup: already applied $(basename "$p")"
  else
    echo "setup: $(basename "$p") does not apply to $pin" >&2; exit 1
  fi
done

# --- 3. recompiler and PCSX2 GS -----------------------------------------------------------------------------------
jobs=${JOBS:-$(nproc 2>/dev/null || echo 4)}
linker=
command -v ld.lld >/dev/null 2>&1 && linker=-DCMAKE_LINKER_TYPE=LLD
cmake -S "$root" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER="${CC:-clang}" -DCMAKE_CXX_COMPILER="${CXX:-clang++}" $linker \
  -DJA_BUILD_RECOMP=ON -DJA_PCSX2_GS=ON
cmake --build "$build" --target ps2_recomp -- -j "$jobs"
cmake --build "$build" --target pcsx2gs -- -j "$jobs"
echo "setup: done. ps2_recomp: $(find "$build" -name ps2_recomp -type f | head -n 1)"
echo "setup: libpcsx2gs.so: $(find "$build" -name 'libpcsx2gs.so' | head -n 1)"
echo "setup: next: tools/extract.sh <dump> (the disc), then the function map (docs/HANDOFF.md)"
