# -*- coding: utf-8 -*-
"""Round 3: fixed word sheets, STRINGS.RES parse, Chinese0.rsb probe, exe/igor greps."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct, os, re
from PIL import Image, ImageDraw

BASE = os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon')
ART = os.path.join(BASE, 'Data', 'Shell', 'Art')
SHELL = os.path.join(BASE, 'Data', 'Shell')
OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'pcfont')

def load_tga_gray(path):
    d = open(path, 'rb').read()
    w, h = struct.unpack_from('<HH', d, 12)
    img = Image.frombytes('RGBA', (w, h), d[18:18 + w * h * 4], 'raw', 'BGRA')
    a = img.split()[3]
    g = Image.composite(Image.new('RGB', img.size, (255, 255, 255)),
                        Image.new('RGB', img.size, (0, 0, 0)), a)
    return g

FILES = {  # fname -> (size, cols, page_index)
    'GB1200.tga': (12, 42, 0),
    'GB1600.tga': (16, 32, 0), 'GB1601.tga': (16, 32, 1),
    'GB2400.tga': (24, 21, 0), 'GB2401.tga': (24, 21, 1), 'GB2402.tga': (24, 21, 2),
}
PER_PAGE = {'GB1200.tga': 42 * 42, 'GB1600.tga': 32 * 32, 'GB1601.tga': 32 * 32,
            'GB2400.tga': 21 * 21, 'GB2401.tga': 21 * 21, 'GB2402.tga': 21 * 21}
cache = {f: load_tga_gray(os.path.join(ART, f)) for f in FILES}

charset = open(os.path.join(ART, 'gbtext.def'), 'rb').read().decode('gbk')

def cell_for(idx, fname):
    size, cols, page = FILES[fname]
    base = sum(PER_PAGE[g] * FILES[g][2] for g in FILES if FILES[g][2] < page)
    li = idx - base
    cx, cy = li % cols, li // cols
    return cache[fname].crop((cx * size, cy * size, (cx + 1) * size, (cy + 1) * size))

def word_sheet(word, outname):
    idxs = [charset.find(ch) for ch in word]
    rows = []
    for fname, scale in [('GB2400.tga', 2), ('GB1600.tga', 3), ('GB1200.tga', 4)]:
        size = FILES[fname][0]
        strip = Image.new('RGB', (len(idxs) * size + 4, size + 4), (255, 255, 255))
        for k, i in enumerate(idxs):
            if i < 0:
                continue
            strip.paste(cell_for(i, fname), (k * size + 2, 2))
        rows.append(strip.resize((strip.width * scale, strip.height * scale), Image.NEAREST))
    W = max(r.width for r in rows)
    H = sum(r.height + 6 for r in rows)
    im = Image.new('RGB', (W, H), (225, 225, 235))
    y = 0
    for r in rows:
        im.paste(r, (0, y)); y += r.height + 6
    im.save(os.path.join(OUT, outname))
    print('saved', outname, word, 'idx', idxs)

for w in ['玩家', '胜利', '任务', '隐藏行动', '更换弹夹']:
    word_sheet(w, 'word2_%s.png' % w)

# ---------- STRINGS.RES parse ----------
print('===== STRINGS.RES =====')
d = open(os.path.join(SHELL, 'STRINGS.RES'), 'rb').read()
print('size', len(d))
# hypothesis: [u32 n][u32 klen][key][u32 vlen][value] with vlen = full struct size?
# from hex: n=0x53? then 9 "GameType0" then 00 04 00 00 00 06 00 00 00 -> maybe two u32: 0x0400? no
# alternative: [u32 n][entries]: entry=[u32 klen][key\0?][u32 vlen][value\0]
# test: klen=9, key 9B "GameType0", then bytes 17-20 = 00 04 00 00 -> 0x400
# but next key "GameType1" appears ~byte 104: so entry stride ~ 96 = 4+9+?; 104-13=91
# try: vlen at 17 = 0x00000400?? no. Let's brute force: find "GameType1" offset
i1 = d.find(b'GameType1')
i0 = d.find(b'GameType0')
print('GameType0 at', i0, 'GameType1 at', i1, 'stride', i1 - i0)
print('bytes 17..40:', d[17:40].hex())
# stride 96: klen(4)+key(9)+X -> value buffer 0x50=80? 4+9+4+80 = 97 close
# maybe value len = 0x50 = 80: 4+9+4 = 17, value 80 -> next at 97? but i1-i0=96
# maybe klen stored as 1 byte? layout: klen u32, key, vlen u32, value vlen bytes
# with vlen=0x50=80: entry1 = 4+9+4+80 = 97. Hmm i1-i0 = 96. so vlen=79? weird
# OR klen is u8: entry = klen(1)+9+vlen(1)+80 = 91 -> 104-13 = 91 !!
# so: [u8 klen][key][u8 vlen][value]. entry1: klen=9? but byte0..3 = 53 00 00 00 -> n=0x53?
# entry starts at 4: klen byte = 09, key 9B, vlen byte = 00?? no...
# try: entry = [u32 klen][key][u32 vlen][value vlen], vlen = 0x400 = 1024? no (stride 96)
print('d[0:4]=', d[0:4].hex(), 'd[4]=', d[4], 'd[5:5+9]=', d[5:14], 'd[14:18]=', d[14:18].hex())
vlen = struct.unpack_from('<I', d, 14)[0]
print('vlen guess at 14:', vlen)
print('d[18:26]:', d[18:26].hex(), 'next key at 18+vlen?', d[18+vlen:18+vlen+16])
