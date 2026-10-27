#!/bin/sh
# Run the game (docs/SETUP.md). A window opens on the desktop (WSLg under WSL2).
#   tools/launch.sh [--iso <image>] [--seconds N] [--software-gs] [extra args for the program]
# Defaults: the ISO at private/jackass.iso (tools/extract.sh), PCSX2's GS on Vulkan (libpcsx2gs.so next to the
# program), the ImGui debugger closed (F1 opens it), logs in private/logs/jackass-<time>.log. --seconds N ends the
# run after N seconds (smoke tests). --software-gs runs the runtime's own software GS instead (the slow stand-in).
# Runtime env the user can still set: PS2X_* (see the Urban Reign port's docs/ENV.md in engine/runtime/docs).
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=$root/build/linux/bin
iso=$root/private/jackass.iso
seconds=
while [ $# -gt 0 ]; do
  case "$1" in
    --iso) iso=$2; shift ;;
    --seconds) seconds=$2; shift ;;
    --software-gs) export PS2X_GS_RENDERER=software ;;   # anything but "pcsx2" keeps the runtime's own GS
    --) shift; break ;;
    *) break ;;
  esac
  shift
done
[ -x "$bin/jackass" ] || { echo "launch: $bin/jackass not built: tools/build.sh" >&2; exit 1; }
[ -f "$iso" ] || { echo "launch: no disc image at $iso (tools/extract.sh)" >&2; exit 1; }
mkdir -p "$root/private/logs"
log=$root/private/logs/jackass-$(date +%Y%m%d-%H%M%S).log
export JA_USER_DIR=${JA_USER_DIR:-$root/private/user}
mkdir -p "$JA_USER_DIR"
echo "launch: $bin/jackass --iso $iso  (log: $log)"
cd "$bin"
if [ -n "$seconds" ]; then
  timeout --signal=INT --kill-after=5 "$seconds" ./jackass --iso "$iso" "$@" > "$log" 2>&1 || true
else
  ./jackass --iso "$iso" "$@" 2>&1 | tee "$log"
fi
echo "launch: log at $log"
