# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/zh7_build.py (逐字复制 (ZH7 一体构建参照实现; 顶层执行不可 import, 参数化版见 build/example_zh7))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""zh7_build.py — GR_ZH7 阶段2 构建器: FONT.RES(rows 重排+160 DBCS) + COMMON.PAK(收割格+绘制)
                   + EN_STRINGS.RES(zh6 76 条 + 新 524 条 DBCS 扩译) → MENU_ZH7.img

前置: SLUS_P_T.elf = P-S + lhu 修复 (build_PS_v4.py; GR_DB7 已实证 DBCS 对渲染汉字)
face 预算: large rows5(160: 0x20-0xBF, 保 ®±µ/0x92) + default rows12(384: 原224 含 zh6 89 字
           + idx224-383 = 160 DBCS) + huge rows7(112: 0x20-0x8F ASCII) → 7066B ≤ 7222
DBCS 编码: 第 k 字 → (lead,trail) = (0xA1+k//94, 0xA1+k%94), idx = 224+k
atlas: 收割被裁撤记录的格 (large 0xC0+/huge 0x90+/default 0x7F-0xA0 占位) 清底,
       按 26px 带排 16px SimHei 格 (u0≥1 规避 0xA1 诅咒); 保留记录矩形全程避让
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys, json, os
import numpy as np
from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img_patch import parse_entries
from ft_dpc import dp_compress
from lz77_decode import decode_entry, lzo1x_decompress
from lzo1x_c import compress as lzo_compress

HAN = os.path.join(REPO_ROOT, 'docs', 'han_v2')
SRC_IMG = HAN + r'\menu_working\MENU.IMG'
ZH6_FT = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh6', 'ft_expanded_zh6.bin')
ZH6_PAK = HAN + r'\COMMON_PAK_ZH6.bin'
V3 = os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_zh_8sub_v3.bin')
ZH6_CS = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh6', 'charset_zh6.json')
SEL = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh7_sel.json')
OUT_DIR = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh7')
SURF = 0x1069
REAL = 128545
CHUNKS = [16384] * 7 + [13857]
SLOT_STORED, PAYLOAD_MAX = 4421, 4413
PROT = {0xAE, 0xB1, 0xB5, 0xE7, 0xF1}
import os
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- 解析 zh6 展开态字体 ----------
ft6 = open(ZH6_FT, 'rb').read()
def parse_faces(ft):
    p = 0
    sl = struct.unpack_from('<I', ft, p)[0]; p += 4 + sl
    n = struct.unpack_from('<I', ft, p)[0]; p += 4
    faces = []
    for f in range(n):
        l = struct.unpack_from('<I', ft, p)[0]; p += 4
        nm = ft[p:p+l].decode('latin-1'); p += l
        fld = list(struct.unpack_from('<14I', ft, p)); p += 56
        nrec = fld[4] * fld[5]
        recs = [struct.unpack_from('<BB4H', ft, p + 10*r) for r in range(nrec)]
        p += nrec * 10
        faces.append((nm, fld, recs))
    ns = struct.unpack_from('<I', ft, p)[0]; p += 4
    styles = ft[p:]
    return faces, ns, styles
F6, NS, STYLES = parse_faces(ft6)
assert [f[0] for f in F6] == ['large', 'default', 'huge']
large_r = F6[0][2]; def_r = F6[1][2]; huge_r = F6[2][2]
tex = ft6[4:4+20]
assert tex == b'new_font_revised.rsb'

# ---------- 字符集 ----------
cs6 = json.load(open(ZH6_CS, encoding='utf-8'))
codes89 = cs6['codes']                       # hanzi -> byte
sel = json.load(open(SEL, encoding='utf-8'))
dbcs = sel['dbcs_ordered']                   # 157 新字, 频次序
MARK_CODES = (0xA1, 0xA2, 0xA3)              # 对前导标记码 (v5 ELF: 仅此三码作 lead)
hz_of_code = {v: k for k, v in codes89.items()}
MARKERS = [hz_of_code[c] for c in MARK_CODES]   # 役/有/下 → 字符串中一律以对形式编码
assert len(dbcs) <= 188
pair_of = {}
for k, ch in enumerate(dbcs):
    pair_of[ch] = (0xA1 + k // 94, 0xA1 + k % 94)
# 标记字符的对形式: 占 idx 381-383 (= (0xA2,E0/E1/E2)), 字形复用其 ZH6 单字节格
mk_pair = {ch: (0xA2, 0xE0 + j) for j, ch in enumerate(MARKERS)}
pair_of.update(mk_pair)
for ch in MARKERS:
    assert ch in codes89 and codes89[ch] in MARK_CODES

# ---------- 1) FONT.RES 重排 ----------
ROWS = {'large': 5, 'default': 12, 'huge': 7}
out = bytearray()
out += struct.pack('<I', 20) + tex
out += struct.pack('<I', 3)
tbl_off = {}
for nm, fld, recs in F6:
    rows = ROWS[nm]
    keep = [0] + [r for r in recs]           # 占位; 下面真写
    l = len(nm)
    out += struct.pack('<I', l) + nm.encode()
    fld = list(fld); fld[5] = rows
    tbl_off[nm] = len(out) + 56
    out += struct.pack('<14I', *fld)
    nrec = fld[4] * rows
    for i in range(nrec):
        if i < len(recs):
            out += struct.pack('<BB4H', *recs[i])
        else:
            out += struct.pack('<BB4H', 0, 10, 0, 0, 0, 0)
out += struct.pack('<I', NS) + STYLES
# DBCS 记录区 = default 表 idx224-383 (在 huge face 之前, 校验不越界)
dbcs_foff = tbl_off['default'] + 224 * 10
assert dbcs_foff + 160 * 10 <= tbl_off['huge'], (hex(dbcs_foff), hex(tbl_off['huge']))
# 回填: DBCS 记录的 u0/v0 需 atlas 排布 → 先排 atlas 再回填, FONT 的非 DBCS 部分已定

# ---------- 2) atlas 收割 + 排格 ----------
pak = bytearray(open(ZH6_PAK, 'rb').read())
A = np.frombuffer(bytes(pak[SURF:SURF+512*512]), dtype=np.uint8).reshape(512, 512).copy()
def rect_of(r):
    pad, adv, u0, v0, u1, v1 = r
    return (u0 + 20, v0, u1 + 20, v1)
kept = []
for c in range(0x20, 0xC0): kept.append(rect_of(large_r[c-0x20]))
for c in range(0x20, 0x100):
    if 0x7F <= c <= 0xA0 and c != 0x92: continue   # 占位虚线格 → 收割 (EN 零使用)
    kept.append(rect_of(def_r[c-0x20]))
for c in range(0x20, 0x90): kept.append(rect_of(huge_r[c-0x20]))
def inter(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
cands = []
for c in range(0xC0, 0x100): cands.append(rect_of(large_r[c-0x20]))
for c in range(0x90, 0x100): cands.append(rect_of(huge_r[c-0x20]))
for c in range(0x7F, 0xA1):
    if c != 0x92: cands.append(rect_of(def_r[c-0x20]))
cleared = []
for r in cands:
    if any(inter(r, k) for k in kept): continue
    x0, y0, x1, y1 = [max(0, v) for v in r]
    x1, y1 = min(512, x1), min(512, y1)
    if x1 <= x0 or y1 <= y0: continue
    A[y0:y1, x0:x1] = 31
    cleared.append((x0, y0, x1, y1))
print('[atlas] 收割清底 %d 矩形' % len(cleared))

# 26px 带自由 run (避开 kept 矩形 + 现存墨)
def free_runs(y0, y1):
    blocked = np.zeros(512, dtype=bool)
    for (kx0, ky0, kx1, ky1) in kept:
        if ky0 < y1 and ky1 > y0:
            blocked[max(0, kx0):min(512, kx1)] = True
    ink = (A[y0:y1, :] != 31).any(axis=0)
    blocked |= ink
    runs, x = [], 21                       # u0 ≥ 1
    while x < 512:
        if blocked[x]:
            x += 1; continue
        y = x
        while y < 512 and not blocked[y]: y += 1
        if y - x >= 16: runs.append((x, y))
        x = y
    return runs
CELL_W, CELL_H, ADV16 = 16, 26, 16
placement = []                              # (band_y0, sx)
for y0 in list(range(0, 512 - CELL_H, 13)):
    for (a, b) in free_runs(y0, y0 + CELL_H):
        x = a
        while x + CELL_W <= b:
            placement.append((y0, x))
            x += CELL_W
placement.sort(key=lambda t: (t[0], t[1]))
# 过滤: 与已选格互不重叠 (带步进 13 < 26 → 上下带重叠, 需二维去重)
chosen = []
occ = np.zeros((512, 512), dtype=bool)
for (y0, x) in placement:
    if occ[y0:y0+CELL_H, x:x+CELL_W].any(): continue
    occ[y0:y0+CELL_H, x:x+CELL_W] = True
    chosen.append((y0, x))
    if len(chosen) == len(dbcs): break
print('[atlas] 排格 %d / 需 %d' % (len(chosen), len(dbcs)))
assert len(chosen) == len(dbcs), 'atlas 容量不足'

f16 = ImageFont.truetype(r'D:\Document\Fonts\SimHei.ttf', 16)
for k, ch in enumerate(dbcs):
    y0, x = chosen[k]
    A[y0:y0+CELL_H, x:x+CELL_W] = 31
    m = f16.getmask(ch, mode='L')
    w, h = m.size
    assert h == 16 and 0 < w <= 16, (ch, m.size)
    ga = np.asarray(m, dtype=np.uint8).reshape(h, w)
    tx = np.where(ga > 128, 0, 31).astype(np.uint8)
    py = y0 + (CELL_H - 16) // 2
    A[py:py+16, x:x+16] = tx
pak[SURF:SURF+512*512] = A.tobytes()
open(OUT_DIR + r'\COMMON_PAK_ZH7.bin', 'wb').write(bytes(pak))

# DBCS 记录回填 (u0 = x-20, v0 = y0, adv=16); idx 381-383 = 标记字对 → 复用 ZH6 单字节格
dbcs_recs = []
for k in range(len(dbcs)):
    y0, x = chosen[k]
    dbcs_recs.append((0, ADV16, x - 20, y0, x - 20 + CELL_W, y0 + CELL_H))
for j, ch in enumerate(MARKERS):
    pad, adv, u0, v0, u1, v1 = def_r[MARK_CODES[j] - 0x20]
    dbcs_recs.append((pad, adv, u0, v0, u1, v1))
assert len(dbcs_recs) == 160 and 224 + len(dbcs_recs) - 1 <= 383
layout = open(OUT_DIR + r'\layout_dbcs.txt', 'w', encoding='utf-8')
for k, ch in enumerate(dbcs):
    y0, x = chosen[k]
    layout.write('idx=%d %s (%02X,%02X) cell=(%d,%d) rec=(%d,%d,%d,%d,16)\n' %
                 (224+k, ch, pair_of[ch][0], pair_of[ch][1], x, y0,
                  x-20, y0, x-20+CELL_W, y0+CELL_H))
for j, ch in enumerate(MARKERS):
    pad, adv, u0, v0, u1, v1 = def_r[MARK_CODES[j] - 0x20]
    layout.write('idx=%d %s* (%02X,%02X) 复用单字节格 rec=(%d,%d,%d,%d,%d)\n' %
                 (381+j, ch, mk_pair[ch][0], mk_pair[ch][1], u0, v0, u1, v1, adv))
layout.close()

# FONT: DBCS 记录写入 default 表 idx 224-383
for k, rec in enumerate(dbcs_recs):
    struct.pack_into('<BB4H', out, dbcs_foff + 10*k, *rec)
expanded = bytes(out)
print('[FONT] 展开态 %dB (≤7222)' % len(expanded))
assert len(expanded) <= 7222
# 解析回环
F7, NS7, ST7 = parse_faces(expanded)
assert [f[0] for f in F7] == ['large', 'default', 'huge']
assert F7[0][1][5] == 5 and F7[1][1][5] == 12 and F7[2][1][5] == 7
assert ST7 == STYLES and NS7 == NS
payload = dp_compress(expanded, verbose=False)
print('[FONT] payload %dB (限 %d)' % (len(payload), PAYLOAD_MAX))
assert len(payload) <= PAYLOAD_MAX
frame = struct.pack('<II', len(payload), len(expanded)) + payload
slot = frame + b'\x00' * (SLOT_STORED - len(frame))
back, stats = decode_entry(slot)
assert back == expanded and all(s[3] is None for s in stats)
open(OUT_DIR + r'\ft_expanded_zh7.bin', 'wb').write(expanded)
open(OUT_DIR + r'\ft_slot_zh7.bin', 'wb').write(slot)
print('[FONT] 槽回环 PASS')

# ---------- 3) EN_STRINGS.RES ----------
def decode_blob(fr):
    p, outb = 0, []
    while p + 8 <= len(fr):
        plen, o = struct.unpack_from('<II', fr, p)
        dec, err, _ = lzo1x_decompress(fr[p+8:p+8+plen], out_size=o)
        assert err is None and len(dec) == o
        outb.append(dec); p += 8 + plen
    return b''.join(outb)
def walk(data):
    p = 0
    ng = struct.unpack_from('<I', data, p)[0]; p += 4
    groups = []
    for g in range(ng):
        if g > 0: p += 4
        cnt = struct.unpack_from('<I', data, p)[0]; p += 4
        st = []
        for i in range(cnt):
            ln = struct.unpack_from('<I', data, p)[0]; p += 4
            st.append(bytearray(data[p:p+ln])); p += ln + 2
        groups.append(st)
    assert data[p:p+8] == b'\x00'*8
    return groups, p + 8
def serialize(groups, total):
    o = bytearray(); o += struct.pack('<I', len(groups))
    for gi, st in enumerate(groups):
        if gi: o += struct.pack('<I', 0)
        o += struct.pack('<I', len(st))
        for s in st: o += struct.pack('<I', len(s)) + bytes(s) + b'\x00\x00'
    o += b'\x00' * 8
    assert len(o) <= total, (len(o), total)
    o += b'\x00' * (total - len(o))
    return bytes(o)
def encode(text):
    b = bytearray()
    for ch in text:
        if ch in codes89 and ch not in MARKERS:
            cd = codes89[ch]
            assert cd not in MARK_CODES, (ch, text)   # 标记码不得作单字节出现
            b.append(cd)
        elif ch in pair_of:
            l, t = pair_of[ch]; b += bytes((l, t))
        else:
            v = ord(ch)
            assert 0x20 <= v < 0x7F, (repr(ch), text)
            b.append(v)
    assert not any(0x80 <= x <= 0x9F for x in b)
    return bytes(b)

cont = decode_blob(open(V3, 'rb').read())
assert len(cont) == REAL
groups, total = walk(cont)
n = 0
for tk, text in cs6['translations'].items():
    g = int(tk[1:tk.index('.')]) - 1; i = int(tk[tk.index('I')+1:])
    groups[g][i] = bytearray(encode(text)); n += 1
for tk, text in cs6['new_entries'].items():
    g = int(tk[1:tk.index('.')]) - 1; i = int(tk[tk.index('I')+1:])
    groups[g][i] = bytearray(encode(text)); n += 1
n7 = 0
for c in sel['entries']:
    key = c['key']
    g = int(key[1:key.index('.')]) - 1; i = int(key[key.index('.I')+2:])
    groups[g][i] = bytearray(encode(c['zh'])); n7 += 1
print('[RES] zh6 %d 条 + zh7 新 %d 条' % (n, n7))
cont2 = serialize(groups, REAL)
assert walk(cont2)[0] == groups
pos, frames = 0, []
for csz in CHUNKS:
    chunk = cont2[pos:pos+csz]
    pl = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
    back, err, _ = lzo1x_decompress(pl, out_size=csz)
    assert err is None and back == chunk
    frames.append(struct.pack('<II', len(pl), csz) + pl)
    pos += csz
blob = b''.join(frames)
assert decode_blob(blob) == cont2
print('[RES] blob %dB (槽限 47570, 余 %d)' % (len(blob), 47570 - len(blob)))
assert len(blob) <= 47570
open(OUT_DIR + r'\en_strings_zh7_8sub.bin', 'wb').write(blob)
open(OUT_DIR + r'\container_zh7.bin', 'wb').write(cont2)

# ---------- 4) 组装 MENU_ZH7.img ----------
img = bytearray(open(SRC_IMG, 'rb').read())
base = bytes(img)
ents = parse_entries(base)
e = ents['FONT.RES']
assert e['stored'] == SLOT_STORED and e['real'] == 7222
img[e['off']:e['off']+SLOT_STORED] = slot
ep = ents['COMMON.PAK']
pak_src = open(OUT_DIR + r'\COMMON_PAK_ZH7.bin', 'rb').read()
assert len(pak_src) == ep['stored'] == ep['real']
img[ep['off']:ep['off']+len(pak_src)] = pak_src
e3 = ents['EN_STRINGS.RES']
img[e3['off']:e3['off']+len(blob)] = blob

# 自检: 差异白名单
ok = len(img) == len(base)
tab_end = struct.unpack_from('<I', base, 4)[0]
names_off = struct.unpack_from('<I', base, 0x10)[0]
ok = ok and all(struct.unpack_from('<12I', base, 0x830 + 48*i) ==
                struct.unpack_from('<12I', bytes(img), 0x830 + 48*i)
                for i in range(struct.unpack_from('<I', base, 0x24)[0] if False else 686))
rs = []
i, nn = 0, len(base)
while i < nn:
    if base[i] != img[i]:
        j = i
        while j < nn and base[j] != img[j]: j += 1
        rs.append((i, j)); i = j
    else:
        i += 1
white = [(e['off'], e['off']+SLOT_STORED),
         (ep['off'], ep['off']+len(pak_src)),
         (e3['off'], e3['off']+len(blob))]
bad = [r for r in rs if not any(r[0] >= lo and r[1] <= hi for lo, hi in white)]
ok = ok and not bad
print('[DIFF] %d 区段, 白名单外 %d' % (len(rs), len(bad)))
DST = os.path.join(REPO_ROOT, 'work', 'tmp', 'MENU_ZH7.img')
open(DST, 'wb').write(bytes(img))
print('[BUILD] %s (%s)' % (DST, 'PASS' if ok else 'FAIL'))
sys.exit(0 if ok else 2)
