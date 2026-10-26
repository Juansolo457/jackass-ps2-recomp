"""List or extract a PS2 DVD image (plain ISO 9660, 2048-byte sectors), with no dependencies.

    python3 -I tools/iso9660.py list   <image.iso>
    python3 -I tools/iso9660.py extract <image.iso> <out_dir>
    python3 -I tools/iso9660.py cat    <image.iso> <PATH/ON/DISC>

PS2 discs are ISO 9660 level 1 (8.3 upper-case names, ';1' versions); Joliet is ignored on
purpose so paths match what SYSTEM.CNF and the game's own code use. The ';1' suffix is kept on
disc paths and stripped from extracted file names. The image is only ever read.
"""
import os
import struct
import sys

SECTOR = 2048


class Entry:
    __slots__ = ('name', 'path', 'is_dir', 'lba', 'size')

    def __init__(self, name, path, is_dir, lba, size):
        self.name, self.path, self.is_dir, self.lba, self.size = name, path, is_dir, lba, size


def read_sector(f, lba, count=1):
    f.seek(lba * SECTOR)
    return f.read(count * SECTOR)


def parse_record(rec):
    """One directory record -> (name, is_dir, lba, size); name '\x00'/'\x01' are . and .."""
    lba = struct.unpack_from('<I', rec, 2)[0]
    size = struct.unpack_from('<I', rec, 10)[0]
    flags = rec[25]
    name_len = rec[32]
    raw = rec[33:33 + name_len]
    if raw in (b'\x00', b'\x01'):
        name = '.' if raw == b'\x00' else '..'
    else:
        name = raw.decode('ascii', 'replace')
    return name, bool(flags & 2), lba, size


def read_dir(f, lba, size, path):
    data = read_sector(f, lba, (size + SECTOR - 1) // SECTOR)[:size]
    pos, out = 0, []
    while pos < len(data):
        length = data[pos]
        if length == 0:  # padding to the next sector
            pos = (pos // SECTOR + 1) * SECTOR
            continue
        name, is_dir, e_lba, e_size = parse_record(data[pos:pos + length])
        pos += length
        if name in ('.', '..'):
            continue
        out.append(Entry(name, f'{path}/{name}' if path else name, is_dir, e_lba, e_size))
    return out


def walk(f):
    pvd = read_sector(f, 16)
    if pvd[0:6] != b'\x01CD001':
        sys.exit('not an ISO 9660 image (no primary volume descriptor at sector 16)')
    vol_id = pvd[40:72].decode('ascii', 'replace').strip()
    root_rec = pvd[156:190]
    _name, _is_dir, lba, size = parse_record(root_rec)
    stack = [('', lba, size)]
    yield ('volume', vol_id, 0, 0)
    while stack:
        path, lba, size = stack.pop()
        for e in sorted(read_dir(f, lba, size, path), key=lambda e: e.path):
            yield ('dir' if e.is_dir else 'file', e.path, e.lba, e.size)
            if e.is_dir:
                stack.append((e.path, e.lba, e.size))


def cmd_list(image):
    total = 0
    with open(image, 'rb') as f:
        for kind, path, lba, size in walk(f):
            if kind == 'volume':
                print(f'volume id: {path}')
            elif kind == 'dir':
                print(f'{"":>12}  {path}/')
            else:
                total += size
                print(f'{size:>12}  {path}  (lba {lba})')
    print(f'{total:>12}  total bytes in files')


def clean_name(path):
    return path[:-2] if path.endswith(';1') else path


def copy_file(f, lba, size, dest):
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    f.seek(lba * SECTOR)
    with open(dest, 'wb') as out:
        left = size
        while left > 0:
            chunk = f.read(min(left, 4 * 1024 * 1024))
            if not chunk:
                raise IOError(f'short read extracting {dest}')
            out.write(chunk)
            left -= len(chunk)


def cmd_extract(image, out_dir):
    n = 0
    with open(image, 'rb') as f:
        for kind, path, lba, size in walk(f):
            if kind == 'file':
                copy_file(f, lba, size, os.path.join(out_dir, *clean_name(path).split('/')))
                n += 1
    print(f'extracted {n} files to {out_dir}')


def cmd_cat(image, path):
    want = clean_name(path.upper().lstrip('/'))
    with open(image, 'rb') as f:
        for kind, p, lba, size in walk(f):
            if kind == 'file' and clean_name(p).upper() == want:
                f.seek(lba * SECTOR)
                sys.stdout.buffer.write(f.read(size))
                return
    sys.exit(f'{path} not on the disc')


def main(argv):
    if len(argv) >= 3 and argv[1] == 'list':
        cmd_list(argv[2])
    elif len(argv) >= 4 and argv[1] == 'extract':
        cmd_extract(argv[2], argv[3])
    elif len(argv) >= 4 and argv[1] == 'cat':
        cmd_cat(argv[2], argv[3])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
