#!/bin/sh
# Turn your disc dump into port/assets/ (docs/SETUP.md):
#   tools/extract.sh /path/to/Jackass.chd      # chdman extractdvd -> private/jackass.iso, then extract
#   tools/extract.sh /path/to/Jackass.iso      # extract an ISO directly
#   tools/extract.sh ... --list                # only list the disc
# The dump is never modified. The ISO lands in private/ (ignored), the files in port/assets/
# (ignored). The ELF's SHA-256 is printed and, if docs/FINDINGS.md already records one, compared.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dump=${1:?usage: tools/extract.sh <dump.chd|dump.iso> [--list]}
mode=${2:-}
mkdir -p "$root/private" "$root/port/assets"

case "$dump" in
  *.chd|*.CHD)
    command -v chdman >/dev/null 2>&1 || { echo "extract: chdman not found (mame-tools); or pass an .iso" >&2; exit 1; }
    iso=$root/private/jackass.iso
    if [ ! -f "$iso" ]; then
      echo "extract: chdman extractdvd -> $iso"
      chdman extractdvd -i "$dump" -o "$iso"
    else
      echo "extract: using existing $iso"
    fi ;;
  *) iso=$dump ;;
esac

if [ "$mode" = "--list" ]; then
  python3 -I "$root/tools/iso9660.py" list "$iso"
  exit 0
fi
python3 -I "$root/tools/iso9660.py" extract "$iso" "$root/port/assets"

cnf=$(find "$root/port/assets" -maxdepth 1 -iname SYSTEM.CNF | head -n 1)
if [ -n "$cnf" ]; then
  boot=$(tr -d '\r' < "$cnf" | sed -n 's/^BOOT2 *= *cdrom0:\\\(.*\);1$/\1/p' | head -n 1)
  echo "extract: SYSTEM.CNF BOOT2 = $boot"
  elf=$root/port/assets/$boot
  if [ -f "$elf" ]; then
    sum=$(sha256sum "$elf" | cut -d' ' -f1)
    echo "extract: $boot SHA-256 $sum"
    if grep -q "$sum" "$root/docs/FINDINGS.md"; then echo "extract: matches docs/FINDINGS.md"
    elif grep -qi 'ELF SHA-256 | (to fill)' "$root/docs/FINDINGS.md"; then echo "extract: record this hash and the game ID in docs/FINDINGS.md"
    else echo "extract: WARNING: hash differs from docs/FINDINGS.md (another release or a bad dump)"; fi
  fi
fi
echo "extract: done -> $root/port/assets"
