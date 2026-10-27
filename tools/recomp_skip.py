"""Rebuild the `skip` list of recomp/jackass.toml: functions the recompiler's own scan finds in the data region
(games/jackass/game.toml [code] data range) that the Ghidra map does not know.

    python3 -I tools/recomp_skip.py            # reads build/generated_staging/ps2_recompiled_functions.h (last generate)
Run after tools/generate.sh when the function map changed; then run generate.sh again.
"""
import csv, os, re, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
LO, HI = 0x5A0000, 0x6A0000
header = os.path.join(ROOT, 'build', 'generated_staging', 'ps2_recompiled_functions.h')
if not os.path.exists(header):
    header = os.path.join(ROOT, 'generated', 'ps2_recompiled_functions.h')
disc = sorted(set(int(m, 16) for m in re.findall(r'sub_([0-9A-F]{8})_0x', open(header).read())))
gh = set(int(r[1], 16) for r in list(csv.reader(open(os.path.join(ROOT, 'recomp', 'jackass_functions.csv'))))[1:])
skip = [a for a in disc if a not in gh and LO <= a < HI]
p = os.path.join(ROOT, 'recomp', 'jackass.toml')
s = open(p, encoding='utf-8').read()
s = re.sub(r'^skip = \[.*?^\]\n', 'skip = [\n' + ''.join(f'  "sub_{a:08X}",\n' for a in skip) + ']\n', s, flags=re.M | re.S)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print(f'{len(skip)} skipped functions in {LO:#x}-{HI:#x} -> recomp/jackass.toml')
