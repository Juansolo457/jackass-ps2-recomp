#!/bin/sh
# Recompile the game's code: ps2_recomp with recomp/jackass.toml over game/<ELF> -> generated/ (docs/SETUP.md).
#   tools/generate.sh            # needs tools/setup.sh (ps2_recomp) and tools/extract.sh (game/) first
# Writes into a staging folder first and copies only changed files into generated/, so an incremental build
# recompiles only what changed (as the Urban Reign port's tools/generate.py does). Game-derived output stays in
# generated/ (ignored). The ELF is checked against the profile's SHA-256 before anything runs.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
game=${GAME:-jackass}
prof() { python3 -I "$root/tools/profile.py" "$game" "$1"; }
elf_name=$(prof executable.name)
elf_sha=$(prof executable.sha256)
map=$root/$(prof runtime.function_map)
template=$root/$(prof runtime.recompiler_template)
elf=$root/game/$elf_name
[ -f "$elf" ] || { echo "generate: $elf missing: run tools/extract.sh first" >&2; exit 1; }
sum=$(sha256sum "$elf" | cut -d' ' -f1)
[ "$sum" = "$elf_sha" ] || { echo "generate: $elf_name SHA-256 $sum is not the profile's $elf_sha" >&2; exit 1; }
recomp=$(find "$root/build/linux" -type f -name ps2_recomp 2>/dev/null | head -n 1)
[ -n "$recomp" ] || { echo "generate: ps2_recomp not built: run tools/setup.sh" >&2; exit 1; }
[ -f "$map" ] || echo "generate: no function map at $map (tools/ghidra_functions.py); the recompiler's own discovery only"

staging=$root/build/generated_staging
rm -rf "$staging"; mkdir -p "$staging" "$root/generated" "$root/build"
sed -e "s|@ELF@|$elf|" -e "s|@MAP@|$map|" -e "s|@OUT@|$staging|" "$template" > "$root/build/jackass.recomp.toml"
echo "generate: $recomp $root/build/jackass.recomp.toml"
"$recomp" "$root/build/jackass.recomp.toml" > "$root/build/recomp.log" 2>&1 || { tail -30 "$root/build/recomp.log"; echo "generate: ps2_recomp failed (build/recomp.log)" >&2; exit 1; }

# Copy only what changed; remove generated files that are no longer produced.
changed=0; removed=0; total=0
for f in "$staging"/*; do
  n=$(basename "$f"); total=$((total+1))
  if ! cmp -s "$f" "$root/generated/$n"; then cp "$f" "$root/generated/$n"; changed=$((changed+1)); fi
done
for f in "$root"/generated/*; do
  [ -e "$f" ] || continue
  n=$(basename "$f")
  if [ ! -e "$staging/$n" ] && [ -f "$f" ]; then rm "$f"; removed=$((removed+1)); fi
done
echo "generate: $total files, $changed written, $removed removed -> generated/"
grep -i -m 5 'warn\|error\|skipped\|functions' "$root/build/recomp.log" || true
