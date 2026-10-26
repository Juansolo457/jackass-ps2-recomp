"""List or extract a PS2 disc image (ISO 9660), with no dependencies.

    python3 -I tools/iso9660.py list    <image>
    python3 -I tools/iso9660.py extract <image> <out_dir>
    python3 -I tools/iso9660.py cat     <image> <PATH/ON/DISC>
    python3 -I tools/iso9660.py toiso   <image> <out.iso>      # rewrite as plain 2048-byte sectors

The image may be a plain ISO (2048 bytes per sector), a raw CD image (2352-byte frames, MODE1
or MODE2/Form1), or what `chdman extractdvd` writes for a CD-type CHD (2448-byte frames: a 2352
slot holding the 2048 user bytes first, then 96 bytes of subcode). The layout is detected from
where the primary volume descriptor ('\\x01CD001') lands at sector 16.

PS2 discs are ISO 9660 level 1 (8.3 upper-case names, ';1' versions); Joliet is ignored on
purpose so paths match what SYSTEM.CNF and the game's own code use. The ';1' suffix is kept on
disc paths and stripped from extracted file names. The image is only ever read.
"""
import os
import struct
import sys

SECTOR = 2048
PVD = b'\x01CD001'
# (frame size, offset of the 2048 user bytes inside the frame)
LAYOUTS = [(2048, 0), (2352, 16), (2352, 24), (2448, 0), (2448, 16), (2448, 24)]


class Entry:
    __slots__ = ('name', 'path', 'is_dir', 'lba', 'size')

    def __init__(self, name, path, is_dir, lba, size):
        self.name, self.path, self.is_dir, self.lba, self.size = name, path, is_dir, lba, size


class Image:
    """A disc image with a detected frame layout; read_sector returns 2048 user bytes per LBA."""

    def __init__(self, f):
        self.f = f
        for frame, skip in LAYOUTS:
            f.seek(16 * frame + skip)
            if f.read(6) == PVD:
                self.frame, self.skip = frame, skip
                break
        else:
            sys.exit('not an ISO 9660 image (no primary volume descriptor at sector 16 in any known layout)')
        f.seek(0, 2)
        self.sectors = f.tell() // self.frame

    def read_sector(self, lba, count=1):
        if self.frame == SECTOR:
            self.f.seek(lba * SECTOR)
            return self.f.read(count * SECTOR)
        out = bytearray()
        for i in range(count):
            self.f.seek((lba + i) * self.frame + self.skip)
            out += self.f.read(SECTOR)
        return bytes(out)

    def describe(self):
        if self.frame == SECTOR:
            return f'plain ISO, {self.sectors} sectors'
        return f'raw frames of {self.frame} bytes, user data at +{self.skip}, {self.sectors} sectors'


def read_sector(img, lba, count=1):
    return img.read_sector(lba, count)


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
    with open(image, 'rb') as raw:
        f = Image(raw)
        print(f'layout: {f.describe()}')
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


def read_file(f, lba, size, sink):
    """Stream a file's bytes (sector-aligned reads, the tail trimmed) into sink(bytes)."""
    left = size
    while left > 0:
        n = min((left + SECTOR - 1) // SECTOR, 2048)   # up to 4 MB of user data per read
        data = f.read_sector(lba, n)
        if len(data) < min(left, n * SECTOR):
            raise IOError('short read')
        sink(data[:min(left, len(data))])
        left -= min(left, n * SECTOR)
        lba += n


def copy_file(f, lba, size, dest):
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    with open(dest, 'wb') as out:
        read_file(f, lba, size, out.write)


def cmd_extract(image, out_dir):
    n = 0
    with open(image, 'rb') as raw:
        f = Image(raw)
        for kind, path, lba, size in walk(f):
            if kind == 'file':
                copy_file(f, lba, size, os.path.join(out_dir, *clean_name(path).split('/')))
                n += 1
    print(f'extracted {n} files to {out_dir}')


def cmd_cat(image, path):
    want = clean_name(path.upper().lstrip('/'))
    with open(image, 'rb') as raw:
        f = Image(raw)
        for kind, p, lba, size in walk(f):
            if kind == 'file' and clean_name(p).upper() == want:
                read_file(f, lba, size, sys.stdout.buffer.write)
                return
    sys.exit(f'{path} not on the disc')


def cmd_toiso(image, out_path):
    with open(image, 'rb') as raw, open(out_path, 'wb') as out:
        f = Image(raw)
        if f.frame == SECTOR:
            sys.exit(f'{image} is already a plain ISO')
        step = 2048
        for lba in range(0, f.sectors, step):
            out.write(f.read_sector(lba, min(step, f.sectors - lba)))
    print(f'wrote {out_path}: {f.sectors} sectors of {SECTOR} bytes')


def main(argv):
    if len(argv) >= 3 and argv[1] == 'list':
        cmd_list(argv[2])
    elif len(argv) >= 4 and argv[1] == 'extract':
        cmd_extract(argv[2], argv[3])
    elif len(argv) >= 4 and argv[1] == 'cat':
        cmd_cat(argv[2], argv[3])
    elif len(argv) >= 4 and argv[1] == 'toiso':
        cmd_toiso(argv[2], argv[3])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
