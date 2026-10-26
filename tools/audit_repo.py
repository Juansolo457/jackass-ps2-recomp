"""Check what git would publish for game material: run before every push (CI runs it too).

    python3 -I tools/audit_repo.py                 every file in the index: tracked plus staged
    python3 -I tools/audit_repo.py --history       every file in every commit (a report: history
                                                   isn't rewritten by anything here)
    python3 -I tools/audit_repo.py --install-hook  run it from .git/hooks/pre-push too (optional)

It reads git's own blobs (git cat-file), never the working tree, so local links to game data or
the toolchain can't hide or add anything. It rejects:
  - folders that only ever hold game material or builds (private/, <port>/assets, generated
    translations under <port>/generated/, logs, saves, caches, build output, the toolchain and
    upstream checkouts);
  - game file types and executable or archive payloads, by extension and by the first bytes
    (ELF, PE/MZ, CHD, ISO 9660, ZIP, 7z, RAR, PS2 PSS movies, VAG/ADPCM audio);
  - recompiled game code (PS2Recomp-style translated functions, or many MIPS instruction
    comments), PS2 game-ID file names, symlinks, submodules and anything over 2 MB, except the
    reviewed exceptions below.

This catches the common accidents, not every copyright question: a clean run doesn't make a
change legally safe. Releases stay source only: never attach builds, game files or the private
test packages (private/) to a release. Adapted from fear360-recomp / graw360-recomp (MIT).
"""
import os
import re
import subprocess
import sys

# Folders that only hold game material, data derived from it, builds or local state.
PROHIBITED_PATHS = [
    (r'(^|/)private/', 'private/ (disc images, traces, captures, test packages)'),
    (r'^game/', 'game/ (the extracted disc)'),
    (r'^data/', 'data/ (prepared discs, recorded VU1 code, dumped IOP modules, saves)'),
    (r'^generated(_[^/]*)?/', 'generated translation of the game code'),
    (r'(^|/)(vu1_capture|iop_modules)/', 'recorded VU1 microcode or dumped IOP modules'),
    (r'^(build|out)/', 'build output'),
    (r'^engine/runtime/', 'the runtime checkout (engine/runtime.toml), fetched by tools/setup.sh'),
    (r'^(\.tools|third_party)(/|$)', 'toolchain or upstream checkout'),
]
# Game files and binaries, by extension.
PROHIBITED_EXTENSIONS = {
    '.chd', '.iso', '.cue', '.bin', '.img', '.elf', '.irx', '.pss', '.ipu', '.vag', '.adx',
    '.exe', '.dll', '.so', '.lib', '.a', '.obj', '.o', '.pdb', '.ilk', '.dmp', '.zip', '.7z',
    '.rar', '.ps2', '.gs', '.nps', '.fsb', '.state',
}
# PS2 executable / game-ID file names (SLUS_216.29 style, SYSTEM.CNF).
GAME_ID_NAME = re.compile(r'(^|/)(S[LC][UEPKA]S_\d{3}\.\d{2}|SYSTEM\.CNF|DISK\.MAP)$', re.I)
# First bytes of executables, archives and game formats.
SIGNATURES = [
    (b'\x7fELF', 'ELF executable'),
    (b'MZ', 'Windows executable (MZ/PE)'),
    (b'MComprHD', 'CHD disc image'),
    (b'PK\x03\x04', 'ZIP archive'),
    (b'7z\xbc\xaf\x27\x1c', '7z archive'),
    (b'Rar!', 'RAR archive'),
    (b'\x00\x00\x01\xba', 'MPEG program stream (PS2 PSS movie)'),
    (b'VAGp', 'PS2 VAG audio'),
    (b'MULTI', 'PS2 MULTI audio bank'),
    (b'IOPRP', 'IOP replacement module image'),
    (b'FSB3', 'FMOD sample bank'),
    (b'FSB4', 'FMOD sample bank'),
]
MAX_SIZE = 2 * 1024 * 1024
# PS2Recomp emits one C++ function per MIPS function; the name patterns below are what its
# generated code and the common hand-written stubs look like. Many MIPS mnemonics in comments
# also mean a translation.
TRANSLATED_FUNCTION = re.compile(rb'\b(void|int)\s+(func|sub|fn)_[0-9A-Fa-f]{6,8}\s*\(')
INSTRUCTION_COMMENT = re.compile(
    rb'^\s*// (lui|addiu|lw|sw|jal|jr|sll|lq|sq|daddu|pextlw|vmulax|vmaddz) ', re.M)
ISO_PVD = b'\x01CD001'  # at offset 0x8000 of an ISO 9660 image; also checked at that offset

# Reviewed exceptions: (path regex, rule it is exempt from, why).
EXCEPTIONS = [
    (r'^engine/patches/.*\.patch$', 'size', "source patches to the runtime checkout, kept so it can be rebuilt"),
]


def git(*args, data=None):
    return subprocess.run(['git', *args], input=data, capture_output=True, check=True).stdout


def exempt(path, rule):
    return any(re.search(pattern, path) and kind in (rule, 'any') for pattern, kind, _ in EXCEPTIONS)


def index_blobs():
    """(mode, sha, path) of every file in the index: what the next commit would contain."""
    out = []
    for entry in git('ls-files', '-s', '-z').split(b'\0'):
        if entry:
            meta, path = entry.split(b'\t', 1)
            mode, sha, _stage = meta.split()
            out.append((mode.decode(), sha.decode(), path.decode('utf-8', 'replace')))
    return out


def history_blobs():
    """(mode, sha, path) of every blob reachable from any ref, under each path it had."""
    out = []
    for line in git('rev-list', '--objects', '--all').decode('utf-8', 'replace').splitlines():
        sha, _, path = line.partition(' ')
        if path:
            out.append(('?', sha, path))
    if not out:
        return out
    types = git('cat-file', '--batch-check=%(objecttype)',
                data=''.join(f'{sha}\n' for _, sha, _ in out).encode()).decode().split()
    return [blob for blob, kind in zip(out, types) if kind == 'blob']


def read_blobs(shas):
    """{sha: content} through one git cat-file --batch."""
    raw = git('cat-file', '--batch', data=''.join(f'{s}\n' for s in shas).encode())
    contents, pos = {}, 0
    while pos < len(raw):
        header_end = raw.index(b'\n', pos)
        sha, _kind, size = raw[pos:header_end].split()
        size = int(size)
        contents[sha.decode()] = raw[header_end + 1:header_end + 1 + size]
        pos = header_end + 1 + size + 1
    return contents


def problems(mode, path, data):
    found = []
    low = path.lower()
    if mode == '120000':
        found.append(('path', 'symlink (could point at game data)'))
    if mode == '160000':
        found.append(('path', 'submodule'))
    for pattern, why in PROHIBITED_PATHS:
        if re.search(pattern, low):
            found.append(('path', why))
    if GAME_ID_NAME.search(path):
        found.append(('path', 'PS2 game executable or SYSTEM.CNF'))
    ext = os.path.splitext(low)[1]
    if ext in PROHIBITED_EXTENSIONS:
        found.append(('extension', f'{ext} file (game data, binary or archive)'))
    if data is None:
        return found
    for magic, why in SIGNATURES:
        if data.startswith(magic) and (magic != b'MZ' or b'\0' in data[:512]):
            found.append(('signature', why))
    if len(data) > 0x8006 and data[0x8000:0x8006] == ISO_PVD:
        found.append(('signature', 'ISO 9660 image'))
    if len(data) > MAX_SIZE:
        found.append(('size', f'{len(data) / 2**20:.1f} MB (over {MAX_SIZE // 2**20} MB)'))
    if len(TRANSLATED_FUNCTION.findall(data)) >= 3 or len(INSTRUCTION_COMMENT.findall(data)) >= 20:
        found.append(('content', 'recompiled game code'))
    return [(rule, why) for rule, why in found if not exempt(path, rule)]


def install_hook():
    hook = os.path.join(git('rev-parse', '--git-path', 'hooks').decode().strip(), 'pre-push')
    if os.path.exists(hook):
        sys.exit(f'{hook} exists already; add "python3 -I tools/audit_repo.py || exit 1" to it.')
    with open(hook, 'w', newline='\n') as f:
        f.write('#!/bin/sh\n# tools/audit_repo.py: no game material in what is pushed.\n'
                'python3 -I tools/audit_repo.py || exit 1\n')
    os.chmod(hook, 0o755)
    print(f'wrote {hook}')


def main():
    os.chdir(git('rev-parse', '--show-toplevel').decode().strip())
    if '--install-hook' in sys.argv:
        install_hook()
        return 0
    history = '--history' in sys.argv
    blobs = history_blobs() if history else index_blobs()
    wanted = sorted({sha for mode, sha, _ in blobs if mode not in ('160000',)})
    contents = read_blobs(wanted) if wanted else {}
    failures = []
    for mode, sha, path in blobs:
        for _rule, why in problems(mode, path, contents.get(sha)):
            failures.append((path, sha, why))
    scope = 'every commit' if history else 'the index (tracked and staged files)'
    if not failures:
        print(f'audit_repo: {len(blobs)} files in {scope}: no game material found.')
        return 0
    print(f'audit_repo: {len(failures)} problem(s) in {scope}:')
    for path, sha, why in sorted(set(failures)):
        print(f'  {path}  [{sha[:10]}]  {why}')
    if history:
        print('These are in history. Removing them from the tree does not remove them from the '
              'commits; rewriting history is a separate decision.')
    else:
        print('Unstage or remove these before committing (git rm --cached keeps a local copy).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
