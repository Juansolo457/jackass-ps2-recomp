"""Locate Sony SDK functions in the stripped ELF and write src/jackass/sdk_functions.inc for the HLE bindings.

Source: upstream PS2Recomp's ps2_analyzer (third_party/PS2Recomp-upstream, built into build/analyzer by
tools/setup-analyzer.sh / by hand) and its embedded SCE symbol database (sce-symbol-scanner: hashes of SDK library
functions, built from games with debug info; Metrowerks 2.4.1.01 among the compilers it saw, the compiler of this
game). The analyzer writes a TOML whose `stubs` (names the runtime has handlers for) and `untracked_stubs` (SDK names
without handlers) carry `name@0xADDRESS` entries; this script turns both into X(address, name, method, score) rows.

    python3 -I tools/sdk_functions.py [--analyzer build/analyzer/ps2xAnalyzer/ps2_analyzer] [--keep-toml]

The HLE bindings (src/jackass/hle_bindings.cpp) then bind the names in their kHleNames list to the runtime's handlers
at start-up; everything else stays recompiled code. Output rows are addresses and SDK names only.
"""
import argparse
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import profile as profiles  # noqa: E402

ENTRY = re.compile(r'"([A-Za-z_][A-Za-z0-9_$.]*)@0x([0-9A-Fa-f]{8})"')


def section(toml, name):
    m = re.search(r'^' + re.escape(name) + r'\s*=\s*\[(.*?)^\]', toml, re.S | re.M)
    return m.group(1) if m else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default='jackass')
    ap.add_argument('--analyzer', default=os.path.join(ROOT, 'build', 'analyzer', 'ps2xAnalyzer', 'ps2_analyzer'))
    ap.add_argument('--toml', help='reuse an analyzer TOML instead of running the analyzer')
    ap.add_argument('--keep-toml', action='store_true')
    args = ap.parse_args()
    prof = profiles.load(args.game)
    elf = os.path.join(ROOT, 'game', prof['executable']['name'])
    out = os.path.join(ROOT, prof['runtime']['sdk_functions'])
    toml_path = args.toml or os.path.join(ROOT, 'private', 'analyzer.toml')
    if not args.toml:
        os.makedirs(os.path.dirname(toml_path), exist_ok=True)
        cmd = [args.analyzer, elf, toml_path]
        print('+', ' '.join(cmd), flush=True)
        subprocess.run(cmd, check=True)
    toml = open(toml_path, encoding='utf-8', errors='replace').read()
    rows = {}
    for kind, method in (('stubs', 'scedb'), ('untracked_stubs', 'scedb-unhandled'), ('entry_points', 'scedb-entry')):
        for name, addr in ENTRY.findall(section(toml, kind)):
            address = int(addr, 16)
            if name.startswith(('sub_', 'FUN_', 'vfunc_')):
                continue
            rows.setdefault(address, (name, method))
    # The Ghidra export (tools/ghidra_functions.py) names the kernel syscall wrappers by their syscall number
    # (SetGsCrt, CreateThread, sceSifSetDma, FlushCache, ...); the SCE database does not carry those.
    ghidra_toml = os.path.join(ROOT, 'private', 'ghidra', 'ghidra_export.toml')
    if os.path.exists(ghidra_toml):
        for name, addr in ENTRY.findall(section(open(ghidra_toml, encoding='utf-8', errors='replace').read(), 'stubs')):
            rows.setdefault(int(addr, 16), (name, 'ghidra-syscall'))
    # libkernel's public SIF loaders are one-call wrappers around the underscore functions the database knows:
    #   sceSifLoadModule(path, arg_len, args)            = _sceSifLoadModule(path, arg_len, args, &local, 0)
    #   sceSifLoadStartModule(path, arg_len, args, res)  = _sceSifLoadModule(path, arg_len, args, res, 0)
    # (and the same pair for _sceSifLoadModuleBuffer). The database misses the wrappers, and the runtime has no
    # LOADFILE server, so an unbound sceSifLoadModule hangs the boot (Killzone port findings). Name them by shape:
    # a short function whose only call is to the underscore function; `a3 = sp` marks the local-result variant.
    elf_data = open(elf, 'rb').read()
    phoff, phnum = struct.unpack_from('<I', elf_data, 0x1C)[0], struct.unpack_from('<H', elf_data, 0x2C)[0]
    segs = [struct.unpack_from('<6I', elf_data, phoff + i * 32) for i in range(phnum)]
    _, seg_off, seg_vaddr, _, seg_size, _ = segs[0]
    words = struct.unpack_from(f'<{seg_size // 4}I', elf_data, seg_off)
    by_name = {name: address for address, (name, _) in rows.items()}
    for inner, local_name, through_name in (('_sceSifLoadModule', 'sceSifLoadModule', 'sceSifLoadStartModule'),
                                           ('_sceSifLoadModuleBuffer', 'sceSifLoadModuleBuffer',
                                            'sceSifLoadStartModuleBuffer')):
        target = by_name.get(inner)
        if target is None:
            continue
        jal = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
        for i, word in enumerate(words):
            if word != jal:
                continue
            # walk back to the prologue (at most 4 instructions) and forward to jr ra (at most 6)
            start = next((i - k for k in range(0, 5) if i - k >= 0 and (words[i - k] >> 16) == 0x27BD
                          and words[i - k] & 0x8000), None)
            end = next((i + k for k in range(1, 7) if i + k < len(words) and words[i + k] == 0x03E00008), None)
            if start is None or end is None:
                continue
            body = words[start:end + 2]
            a3_from_sp = 0x03A0382D in body          # daddu a3, sp, zero
            name = local_name if a3_from_sp else through_name
            address = seg_vaddr + start * 4
            if name not in by_name and address not in rows:
                rows[address] = (name, 'wrapper')
                by_name[name] = address
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// Generated by tools/sdk_functions.py from the PS2Recomp analyzer SCE symbol database - do not edit.\n')
        f.write('// X(guest address, SDK name, match method, similarity)\n')
        for address in sorted(rows):
            name, method = rows[address]
            f.write(f'X(0x{address:08X}u, {name}, "{method}", 1.00f)\n')
    counts = {}
    for name, method in rows.values():
        counts[method] = counts.get(method, 0) + 1
    print(f'{len(rows)} SDK functions -> {os.path.relpath(out, ROOT)} {counts}')
    if not args.keep_toml and not args.toml:
        print(f'analyzer TOML kept at {os.path.relpath(toml_path, ROOT)} (private/)')


if __name__ == '__main__':
    main()
