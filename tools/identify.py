"""Identify a PS2 disc (image or extracted folder) against the game profiles: which game, which edition, and whether
this port's recompiled code is for it.

    python3 -I tools/identify.py <iso|raw image|extracted folder> [...]     one JSON object per disc

Fields: path, elf, game, title, edition, kind (original | unknown), elf_crc, code_sha1, sha256, compatible,
problems[]. Matching: SYSTEM.CNF's BOOT2 name -> profile; the ELF's PCSX2 CRC -> known edition; the SHA-1 of the
profile's code section (`.text`, or `main` for a Metrowerks-linked ELF) decides compatibility.
Images may be plain ISO or raw CD frames (tools/iso9660.py detects the layout). Game data is only ever read.
"""
import functools
import hashlib
import json
import operator
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iso9660  # noqa: E402
import profile as profiles  # noqa: E402


def pcsx2_crc(elf):
    words = struct.iter_unpack('<I', elf[:len(elf) // 4 * 4])
    return '%08X' % functools.reduce(operator.xor, (w for (w,) in words), 0)


def elf_sections(elf):
    """{name: (file offset, size, vaddr)} of an ELF32 little-endian image."""
    e_shoff, = struct.unpack_from('<I', elf, 32)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHH', elf, 46)
    headers = [struct.unpack_from('<10I', elf, e_shoff + i * e_shentsize) for i in range(e_shnum)]
    names = headers[e_shstrndx][4]
    return {elf[names + h[0]:elf.index(b'\0', names + h[0])].decode(): (h[4], h[5], h[3]) for h in headers}


def code_sha1(elf, section):
    off, size, _ = elf_sections(elf)[section]
    return hashlib.sha1(elf[off:off + size]).hexdigest()


def boot_elf_name(system_cnf):
    for line in system_cnf.decode('latin1').splitlines():
        if line.strip().upper().startswith('BOOT2'):
            return line.split('\\')[-1].split(';')[0].strip()
    return ''


class Disc:
    """Root-level files of a disc image or an extracted folder."""

    def __init__(self, path):
        self.path = path
        self.folder = os.path.isdir(path)
        if not self.folder:
            self.raw = open(path, 'rb')
            self.img = iso9660.Image(self.raw)
            self.files = {}
            for kind, p, lba, size in iso9660.walk(self.img):
                if kind == 'file':
                    self.files[iso9660.clean_name(p).upper()] = (lba, size)

    def has(self, name):
        if self.folder:
            return os.path.isfile(os.path.join(self.path, name))
        return name.upper() in self.files

    def read(self, name):
        if self.folder:
            with open(os.path.join(self.path, name), 'rb') as f:
                return f.read()
        lba, size = self.files[name.upper()]
        out = bytearray()
        iso9660.read_file(self.img, lba, size, out.extend)
        return bytes(out)


def identify(path):
    out = {'path': os.path.abspath(path), 'game': None, 'problems': []}
    disc = Disc(path)
    if not disc.has('SYSTEM.CNF'):
        out['problems'].append('no SYSTEM.CNF: not a PS2 game disc')
        return out
    elf_name = boot_elf_name(disc.read('SYSTEM.CNF'))
    out['elf'] = elf_name
    prof = profiles.by_executable(elf_name)
    if prof is None:
        out['problems'].append(f'unknown game (boot ELF {elf_name}): no profile in games/')
        return out
    out.update(game=prof['id'], title=prof['title'])
    elf = disc.read(elf_name)
    out['elf_crc'] = pcsx2_crc(elf)
    out['sha256'] = hashlib.sha256(elf).hexdigest()
    exe = prof['executable']
    try:
        out['code_sha1'] = code_sha1(elf, exe.get('code_section', '.text'))
        code_ok = bool(exe.get('code_sha1')) and out['code_sha1'] == exe['code_sha1']
    except KeyError:
        out['code_sha1'] = None
        code_ok = False
        out['problems'].append(f"the ELF has no {exe.get('code_section', '.text')} section")
    out['compatible'] = code_ok and prof.get('status') != 'planned'
    if not code_ok:
        out['problems'].append('the executable is not the game code this port is built for (other region or build)')
    if prof.get('status') == 'planned':
        out['problems'].append(f"{prof['title']} is not supported yet (status: planned)")
    edition = next((e for e in prof.get('editions', []) if e.get('elf_crc') == out['elf_crc']), None)
    if edition:
        out.update(edition=edition['id'], kind=edition['kind'], language=edition['language'], label=edition['label'])
    else:
        out.update(edition='unknown-' + out['elf_crc'].lower(), kind='unknown', language='unknown',
                   label=f'unrecognised disc {out["elf_crc"]}')
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    json.dump([identify(p) for p in sys.argv[1:]], sys.stdout, indent=1)
    print()
