"""Print a CHD (v5) header: codecs, hunk size, logical size and the metadata tags, read-only.

    python3 -I tools/chd_info.py <image.chd>

Tells you whether chdman will need to do more than zlib/LZMA (a DVD CHD is usually
'lzma', 'zlib', 'huff', 'flac' as the four compressors) and what the DVD metadata says. It does
not decompress anything; use chdman extractdvd for that (tools/extract.sh).
"""
import struct
import sys


def main(path):
    with open(path, 'rb') as f:
        h = f.read(124)
        if h[:8] != b'MComprHD':
            sys.exit('not a CHD file')
        hdr_len, version = struct.unpack('>II', h[8:16])
        print(f'CHD version {version}, header {hdr_len} bytes')
        if version != 5:
            sys.exit('only CHD v5 headers are decoded here')
        codecs = [h[16 + 4 * i:20 + 4 * i].decode('ascii', 'replace').strip('\x00') for i in range(4)]
        logical, map_off, meta_off = struct.unpack('>QQQ', h[32:56])
        hunk, unit = struct.unpack('>II', h[56:64])
        print(f'compressors: {codecs}')
        print(f'logical size {logical} bytes, hunk {hunk} bytes, unit {unit} bytes, '
              f'{(logical + hunk - 1) // hunk} hunks')
        print(f'raw SHA-1 {h[84:104].hex()}  (data), {h[104:124].hex()} (parent)')
        off = meta_off
        while off:
            f.seek(off)
            m = f.read(16)
            tag = m[:4].decode('ascii', 'replace')
            flags_len = struct.unpack('>I', m[4:8])[0]
            length = flags_len & 0xFFFFFF
            nxt = struct.unpack('>Q', m[8:16])[0]
            data = f.read(min(length, 256))
            text = data.rstrip(b'\x00').decode('latin-1', 'replace')
            print(f'metadata {tag} ({length} bytes): {text if text.isprintable() else data[:64].hex()}')
            off = nxt


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
