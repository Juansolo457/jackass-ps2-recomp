#!/bin/bash
# Build the Steam Deck / portable Linux binaries in the Steam Runtime 3 "sniper" SDK container (tools/deck/
# build_release.sh) and package them for your own Deck (tools/deck/make_package.sh).
#   tools/deck/release.sh            # build + package
#   tools/deck/release.sh --build    # build only
#   tools/deck/release.sh --package  # package only (after a build)
# Needs podman (or docker), the generated code (tools/generate.sh) and your disc image (tools/extract.sh).
# Output: $JA_RELEASE_OUT (default ~/jackass-out/release) and private/steamdeck/JackassPS2-SteamDeck.zip.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${JA_RELEASE_OUT:-$HOME/jackass-out/release}
image=registry.gitlab.steamos.cloud/steamrt/sniper/sdk:latest
mode=${1:-all}
engine=$(command -v podman || command -v docker || true)
[ -n "$engine" ] || { echo "release: install podman (or docker)" >&2; exit 1; }
mkdir -p "$out"

if [ "$mode" = all ] || [ "$mode" = --build ]; then
  # generated/ and build/ may be symlinks to an ext4 build root (docs/SETUP.md): mount their targets at the same
  # path inside the container, so the links still resolve there.
  mounts=(-v "$root:/src" -v "$out:$out")
  for link in generated build; do
    if [ -L "$root/$link" ]; then
      target=$(readlink -f "$root/$link")
      mounts+=(-v "$target:$target")
    fi
  done
  "$engine" run --rm "${mounts[@]}" -e JA_RELEASE_OUT="$out" -e JOBS="${JOBS:-$(nproc)}" \
    -w /src "$image" bash /src/tools/deck/build_release.sh
fi
if [ "$mode" = all ] || [ "$mode" = --package ]; then
  JA_RELEASE_OUT="$out" "$root/tools/deck/make_package.sh"
fi
