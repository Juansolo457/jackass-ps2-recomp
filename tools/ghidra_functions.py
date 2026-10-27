"""Build recomp/jackass_functions.csv, the function map that recomp/jackass.toml feeds to ps2_recomp.

Adapted from the Urban Reign port's tools/ghidra_functions.py (GPL-3.0) for this repository's layout and profile:

1. Imports and auto-analyzes the game's ELF (game/<executable.name> from games/jackass/game.toml) in a headless
   Ghidra project (private/ghidra; language r5900:LE:32:default from the ghidra-emotionengine-reloaded extension).
   --no-analyze skips this when the project exists.
2. Exports functions with PS2Recomp's ExportPS2Functions.java (engine/runtime/runtime/ps2xRecomp/tools/ghidra).
3. Keeps only real functions (FUN_*; the export also lists executable labels, which must not become entries),
   drops starts in a branch delay slot plus known bad splits, and cuts each function at the next start so a
   detached tail chunk cannot make one span the whole image.

Usage (inside WSL): python3 -I tools/ghidra_functions.py [--ghidra ~/tools/ghidra_12.1.4_PUBLIC] [--no-analyze]
Everything it reads from the game stays in private/ and game/; only the CSV of addresses goes into recomp/.
"""
import argparse
import bisect
import csv
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import profile as profiles  # noqa: E402

PROJECT_DIR = os.path.join(ROOT, 'private', 'ghidra')
PROJECT = 'Jackass'
SCRIPTS = os.path.join(ROOT, 'engine', 'runtime', 'runtime', 'ps2xRecomp', 'tools', 'ghidra')
# Ghidra splits that land in the middle of a function (checked by hand; add as found).
BAD_STARTS = set()


def headless(ghidra, *args):
    cmd = [os.path.join(ghidra, 'support', 'analyzeHeadless'), PROJECT_DIR, PROJECT, *args]
    print('+', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def is_control_transfer(word):
    op, rs, rt, fn = word >> 26, (word >> 21) & 31, (word >> 16) & 31, word & 63
    return (op in (2, 3) or 4 <= op <= 7 or 0x14 <= op <= 0x17 or (op == 1 and (rt <= 3 or 16 <= rt <= 19)) or
            (op == 0 and fn in (8, 9)) or (op in (0x11, 0x12) and rs == 8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ghidra', default=os.path.expanduser('~/tools/ghidra_12.1.4_PUBLIC'))
    ap.add_argument('--game', default='jackass')
    ap.add_argument('--no-analyze', action='store_true')
    ap.add_argument('--no-export', action='store_true', help='reuse private/ghidra/ghidra_functions.csv')
    args = ap.parse_args()
    prof = profiles.load(args.game)
    elf_name = prof['executable']['name']
    elf_path = os.path.join(ROOT, 'game', elf_name)
    out_csv = os.path.join(ROOT, prof['runtime']['function_map'])
    os.makedirs(PROJECT_DIR, exist_ok=True)
    raw_csv = os.path.join(PROJECT_DIR, 'ghidra_functions.csv')
    if not args.no_analyze:
        headless(args.ghidra, '-import', elf_path, '-processor', 'r5900:LE:32:default', '-overwrite',
                 '-analysisTimeoutPerFile', '3600')
    if not args.no_export:
        headless(args.ghidra, '-process', elf_name, '-noanalysis', '-readOnly', '-scriptPath', SCRIPTS,
                 '-postScript', 'ExportPS2Functions.java', os.path.join(PROJECT_DIR, 'ghidra_export.toml'), raw_csv)

    elf = open(elf_path, 'rb').read()
    phoff, phnum = struct.unpack_from('<I', elf, 0x1C)[0], struct.unpack_from('<H', elf, 0x2C)[0]
    segments = [struct.unpack_from('<6I', elf, phoff + i * 32) for i in range(phnum)]

    def word_at(address):
        for _, offset, vaddr, _, filesz, _ in segments:
            if vaddr <= address < vaddr + filesz:
                return struct.unpack_from('<I', elf, offset + address - vaddr)[0]
        return None

    rows = list(csv.reader(open(raw_csv, newline='')))

    def is_dropped(start):
        previous = word_at(start - 4)
        return start in BAD_STARTS or (previous is not None and is_control_transfer(previous))

    starts = sorted(int(row[1], 0) for row in rows[1:] if row[0].startswith('FUN_') and not is_dropped(int(row[1], 0)))
    kept, dropped, labels = [rows[0]], [], 0
    for row in rows[1:]:
        if not row[0].startswith('FUN_'):
            labels += 1
            continue
        start = int(row[1], 0)
        if is_dropped(start):
            dropped.append(hex(start))
            continue
        # Ghidra's End is the highest address of the body: a detached chunk would make a function span far too much
        # and be emitted again for every such function. Cut at the next start; holes after the body stay with it.
        end = int(row[2], 0)
        following = bisect.bisect_right(starts, start)
        if following < len(starts):
            next_start = starts[following]
            end = next_start if next_start - start <= 0x20000 else min(end, next_start)
        # Same names as the recompiler's own discovery, so generated file names stay stable.
        kept.append([f'sub_{start:08X}', f'0x{start:08X}', f'0x{end:08X}', str(end - start)])
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    csv.writer(open(out_csv, 'w', newline='')).writerows(kept)
    print(f'{os.path.relpath(out_csv, ROOT)}: {len(kept) - 1} functions; {labels} labels skipped; dropped {dropped}')


if __name__ == '__main__':
    main()
