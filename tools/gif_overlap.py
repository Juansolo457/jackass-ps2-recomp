"""Find texture uploads in one field that overwrite GS blocks of a texture uploaded earlier and drawn later.

usage: tools/gif_overlap.py <PS2X_GIF_DUMP file> <field>
Found the texture-ring overwrite behind engine/patches/08 (docs/HANDOFF.md). Groups consecutive uploads with the same DBP into one texture (mips + palette land in their own uploads but are
grouped by the TEX0/CBP that draws them). Block footprints use the GS page/block layouts.
"""
import struct, sys, collections

gif_path, want = sys.argv[1], int(sys.argv[2])
B32 = [[0, 1, 4, 5, 16, 17, 20, 21], [2, 3, 6, 7, 18, 19, 22, 23], [8, 9, 12, 13, 24, 25, 28, 29], [10, 11, 14, 15, 26, 27, 30, 31]]
B16 = [[0, 2, 8, 10], [1, 3, 9, 11], [4, 6, 12, 14], [5, 7, 13, 15], [16, 18, 24, 26], [17, 19, 25, 27], [20, 22, 28, 30], [21, 23, 29, 31]]

def footprint(bp, bw, psm, x0, y0, w, h):
    blocks = set()
    if psm in (0, 1):      # CT32: page 64x32, block 8x8
        pw, ph, bwid, bhei, tab = 64, 32, 8, 8, B32
    else:                  # CT16: page 64x64, block 16x8
        pw, ph, bwid, bhei, tab = 64, 64, 16, 8, B16
    for y in range(y0 - y0 % bhei, y0 + h, bhei):
        for x in range(x0 - x0 % bwid, x0 + w, bwid):
            page = (y // ph) * max(bw, 1) + (x // pw)
            bx = (x % pw) // bwid; by = (y % ph) // bhei
            blocks.add((bp + page * 32 + tab[by][bx]) & 0x3FFF)
    return blocks

def records(path):
    with open(path, 'rb') as f:
        while True:
            h = f.read(5)
            if len(h) < 5:
                return
            n = struct.unpack('<I', h[1:])[0]
            yield chr(h[0]), f.read(n)

regs = {}; field = 0; seq = 0
owner = {}          # block -> (upload seq, dbp)
uploads = []        # (seq, dbp, blocks)
draw_first = {}     # tbp/cbp -> first draw seq in the field
tex_blocks = {}
ctxt = 1; tme = False; tex = {1: 0, 2: 0}

def ad(a, d):
    global ctxt, tme
    regs[a] = d
    if field != want:
        return
    if a == 0x53 and (d & 3) == 0:
        b = regs.get(0x50, 0); p = regs.get(0x51, 0); r = regs.get(0x52, 0)
        dbp = (b >> 32) & 0x3FFF; dbw = (b >> 48) & 0x3F; psm = (b >> 56) & 0x3F
        fp = footprint(dbp, dbw, psm, (p >> 32) & 0x7FF, (p >> 48) & 0x7FF, r & 0xFFF, (r >> 32) & 0xFFF)
        uploads.append((seq, dbp, psm, fp))
    elif a in (6, 7):
        tex[a - 5] = d
    elif a == 0:
        tme = bool(d & 0x10); ctxt = 2 if (d >> 9) & 1 else 1

def draw():
    if field != want or not tme:
        return
    t = tex[ctxt]
    for key in ((t & 0x3FFF), ((t >> 37) & 0x3FFF)):
        draw_first.setdefault(key, seq)

def parse(buf):
    global seq
    i = 0; n = len(buf)
    while i + 16 <= n:
        lo, hi = struct.unpack_from('<QQ', buf, i)
        nloop = lo & 0x7FFF; flg = (lo >> 58) & 3; nreg = (lo >> 60) & 0xF or 16
        pre = (lo >> 46) & 1; prim = (lo >> 47) & 0x7FF
        size = 16 + (nloop * nreg * 16 if flg == 0 else ((nloop * nreg + 1) // 2) * 16 if flg == 1 else nloop * 16)
        if i + size > n:
            break
        seq += 1
        if pre and flg != 2:
            ad(0, prim)
        if flg in (0, 1):
            q = i + 16; step = 16 if flg == 0 else 8
            for _ in range(nloop):
                for r in range(nreg):
                    reg = (hi >> (4 * r)) & 0xF
                    if flg == 0:
                        d, a = struct.unpack_from('<QQ', buf, q)
                        if reg == 0xE: ad(a & 0xFF, d)
                        elif reg in (0, 6, 7): ad(reg, d)
                        elif reg in (4, 5) and not (a >> 47) & 1: draw()
                    else:
                        d = struct.unpack_from('<Q', buf, q)[0]
                        if reg in (0, 6, 7): ad(reg, d)
                        elif reg in (4, 5): draw()
                    q += step
        i += size
    return buf[i:]

pending = b''
for t, p in records(gif_path):
    if t == 'G':
        pending = parse(pending + p)
    elif t == 'V':
        field += 1
        if field > want:
            break

# group uploads by "texture": consecutive uploads whose dbp equals the first one's, plus the palette right after
groups = []
for s, dbp, psm, fp in uploads:
    if groups and (dbp == groups[-1]['dbp'] or (psm == 0 and len(fp) <= 1 and groups[-1]['psm'] != 0)):
        groups[-1]['blocks'] |= fp; groups[-1]['last'] = s
        if len(fp) <= 1: groups[-1]['pal'] = dbp
    else:
        groups.append({'dbp': dbp, 'psm': psm, 'blocks': set(fp), 'first': s, 'last': s, 'pal': None})
print(f'field {want}: {len(uploads)} uploads in {len(groups)} textures')
for g in groups:
    span = f"{min(g['blocks']):#x}-{max(g['blocks']):#x}"
    print(f"  tex dbp={g['dbp']:#x} psm={g['psm']:#x} blocks={len(g['blocks'])} span={span} pal={g['pal'] and hex(g['pal'])} seq={g['first']}..{g['last']} first draw={draw_first.get(g['dbp'])}")
print('overlaps (later upload hits blocks of an earlier texture drawn after it):')
for i, a in enumerate(groups):
    for b in groups[i + 1:]:
        common = a['blocks'] & b['blocks']
        if common:
            d = draw_first.get(a['dbp'])
            victim = d is not None and d > b['first']
            print(f"  {b['dbp']:#x} (seq {b['first']}) overwrites {len(common)} blocks of {a['dbp']:#x} [{min(common):#x}-{max(common):#x}]"
                  f"{' -- VICTIM drawn at %d' % d if victim else ''}")
