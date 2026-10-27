"""Rebuild the `skip` list of recomp/jackass.toml: functions the recompiler's own scan finds outside the profile's
code ranges (games/jackass/game.toml [code] code_ranges) that the function map does not know. Those are data that
happens to decode as instructions (VIF/GIF tags, strings, tables); recompiling them only produces unhandled
instructions.

    python3 -I tools/recomp_skip.py            # reads build/generated_staging/ps2_recompiled_functions.h (last generate)
Run after tools/generate.sh when the function map changed; then run generate.sh again.
"""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import profile as profiles  # noqa: E402

prof = profiles.load('jackass')
ranges = [(int(a, 0), int(b, 0)) for a, b in prof['code']['code_ranges']]
header = os.path.join(ROOT, 'build', 'generated_staging', 'ps2_recompiled_functions.h')
if not os.path.exists(header):
    header = os.path.join(ROOT, 'generated', 'ps2_recompiled_functions.h')
disc = sorted(set(int(m, 16) for m in re.findall(r'sub_([0-9A-F]{8})_0x', open(header).read())))
known = set(int(r[1], 16) for r in list(csv.reader(open(os.path.join(ROOT, prof['runtime']['function_map']))))[1:])
skip = [a for a in disc if a not in known and not any(lo <= a < hi for lo, hi in ranges)]
p = os.path.join(ROOT, prof['runtime']['recompiler_template'])
s = open(p, encoding='utf-8').read()
s = re.sub(r'^skip = \[.*?^\]\n', 'skip = [\n' + ''.join(f'  "sub_{a:08X}",\n' for a in skip) + ']\n', s, flags=re.M | re.S)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print(f'{len(skip)} functions outside the code ranges skipped -> {os.path.relpath(p, ROOT)}')
