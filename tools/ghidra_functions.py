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

    ghidra_starts = {int(row[1], 0) for row in rows[1:] if row[0].startswith('FUN_') and not is_dropped(int(row[1], 0))}
    # Functions reached only through pointers in data, which Ghidra's analysis does not follow:
    # 1. every entry of the profile's static constructor tables ([code] ctor_tables);
    # 2. any aligned word in the image that points into a code range at an `addiu sp, sp, -N` prologue (vtables,
    #    callbacks). Pointer targets without a prologue are not taken: jump tables point inside functions too.
    code = prof.get('code', {})
    code_ranges = [(int(a, 0), int(b, 0)) for a, b in code.get('code_ranges', [])]
    in_code = lambda a: any(lo <= a < hi for lo, hi in code_ranges)
    extra = {}
    for lo, hi in ((int(a, 0), int(b, 0)) for a, b in code.get('ctor_tables', [])):
        for address in range(lo, hi, 4):
            target = word_at(address)
            if target and in_code(target) and target not in ghidra_starts:
                extra[target] = 'ctor'
    # Pointer targets, by what they point at:
    #   prologue: `addiu sp, sp, -N`;
    #   thunk:    `j target` followed by `addiu a0, a0, imm` (Metrowerks this-adjusting thunks in vtables);
    #   empty:    `jr ra` (empty virtual methods);
    #   vtable:   any code pointer stored next to (±4 bytes) a pointer already accepted, repeated to a fixed point.
    # A jump table's entries point inside one function, so they match none of the first three, and a run of them is
    # never next to an accepted function pointer unless the table itself follows a vtable (not seen in this game).
    data_ranges = [(int(a, 0), int(b, 0)) for a, b in [code.get('data_range', ['0', '0'])]]
    image = []  # (address, value) of every aligned word of every loaded segment
    for _, offset, vaddr, _, filesz, _ in segments:
        for i in range(0, filesz - 3, 4):
            image.append((vaddr + i, struct.unpack_from('<I', elf, offset + i)[0]))
    value_at = dict(image)

    def shape(target):
        first, second = word_at(target), word_at(target + 4)
        if first is None:
            return None
        if (first >> 16) == 0x27BD and first & 0x8000:
            return 'pointer'
        if (first >> 26) == 0x02 and second is not None and (second >> 16) == 0x2484:
            return 'thunk'
        if first == 0x03E00008:
            return 'empty'
        return None

    accepted_slots = set()
    for address, target in image:
        if target & 3 or not in_code(target):
            continue
        if target in ghidra_starts or target in extra:
            accepted_slots.add(address)
            continue
        kind = shape(target)
        if kind:
            extra[target] = kind
            accepted_slots.add(address)
    changed = True
    while changed:
        changed = False
        for address, target in image:
            if address in accepted_slots or target & 3 or not in_code(target):
                continue
            if any(lo <= target < hi for lo, hi in data_ranges):
                continue
            if (address - 4) in accepted_slots or (address + 4) in accepted_slots:
                if target not in ghidra_starts and target not in extra:
                    extra[target] = 'vtable'
                accepted_slots.add(address)
                changed = True
    # Every pointer-reached start must sit on a function boundary: after padding (a zero word), or after a return or
    # an unconditional jump and its delay slot. This drops matches inside a function, e.g. an epilogue's
    # `jr ra; addiu sp, sp, N` that the empty-method shape would otherwise take (33 such in this game).
    def at_boundary(target):
        before1, before2 = word_at(target - 4), word_at(target - 8)
        return before1 == 0 or before2 == 0x03E00008 or (before2 is not None and (before2 >> 26) == 0x02)
    rejected = sorted(t for t, kind in extra.items() if kind != 'ctor' and not at_boundary(t))
    for t in rejected:
        del extra[t]
    starts = sorted(ghidra_starts | set(extra))
    kept, dropped, labels = [rows[0]], [], 0
    for start in sorted(extra):
        rows.append([f'PTR_{start:08X}', f'0x{start:08X}', f'0x{start + 4:08X}', '4'])
    for row in rows[1:]:
        if not row[0].startswith(('FUN_', 'PTR_')):
            labels += 1
            continue
        start = int(row[1], 0)
        if row[0].startswith('FUN_') and is_dropped(start):
            dropped.append(hex(start))
            continue
        if row[0].startswith('PTR_'):
            # a pointer-reached start: its end is the next start, like every other row (set below)
            row = [row[0], row[1], f'0x{start + 0x20000:08X}', '0']
        # Ghidra's End is the highest address of the body: a detached chunk would make a function span far too much
        # and be emitted again for every such function. Cut at the next start; holes after the body stay with it.
        end = int(row[2], 0)
        following = bisect.bisect_right(starts, start)
        if following < len(starts):
            next_start = starts[following]
            end = next_start if next_start - start <= 0x20000 else min(end, next_start)
        # Same names as the recompiler's own discovery, so generated file names stay stable.
        kept.append([f'sub_{start:08X}', f'0x{start:08X}', f'0x{end:08X}', str(end - start)])
    kept[1:] = sorted(kept[1:], key=lambda r: int(r[1], 16))
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    csv.writer(open(out_csv, 'w', newline=''), lineterminator='\n').writerows(kept)
    kinds = {k: sum(1 for v in extra.values() if v == k) for k in ('ctor', 'pointer', 'thunk', 'empty', 'vtable')}
    print(f'{os.path.relpath(out_csv, ROOT)}: {len(kept) - 1} functions ({len(ghidra_starts)} Ghidra, '
          f'pointer-reached {kinds}); {len(rejected)} pointer targets inside functions rejected; '
          f'{labels} labels skipped; dropped {dropped}')


if __name__ == '__main__':
    main()
