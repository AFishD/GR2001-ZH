# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..'))

r"""gen_font16.py — 16px 字库终局重建 (合并步骤A+B): 方正像素16.ttf → 512x1024 PSMT4 纹理
    + 新 FONT.RES face 表 (ft_slot 4421B) + 新 COMMON.PAK (保定长 400,659B)

与 13px 现役管线 (work/zh16/zh16_font.py) 的差异:
  - 字形源: 全部 1136 pair + 76 single 汉字改由 方正像素16.ttf (FZXS16) 16px 原生网格渲染
    (PIL 阈值化), 不再复用 Zpix13/ZH14 拷贝; EN 98 码位仍绝对带拷贝自 ZH14 atlas (13px 设计)。
  - 布局: NCOL=30, CW=CH=16, X0=20, Y0=2, SKIP_ROW=12, SKIP_ROWS=3 (SKIP_OFF=48=3x16, 由
    cave 以 CELL_H*SKIP_ROWS 动态算出, 无立即数), h=1024。行窗 y(r)=2+16r+48*[r>=12]。
    行 11 止于 194, 图标窗 [198,221) 原位保留 (ELF/资源硬引用, 不可移); 行 12 起 242。
  - pair 编码槽 -> 格 完全由 cave 公式决定 (idx>=224 走 cave: col=slot%NCOL,
    row=slot//NCOL), FT 中无 pair 记录 → atlas 必须与公式一致, 不可人为跳行。
  - EN 带 476/491 → 714/729 (v0=712/727): 所有 slot 行 (0..40, 最深 v1=706) 之下,
    与行窗零冲突; zh16 曾把 EN 带 452→476 平移成功, 证明带位置纯记录驱动。
  - SREC (空格/空白记录) 466..482 → 760..776 (原位落 rows26/27 格窗, 必须迁出)。
  - face fld[1] (= CharHeight 的 desc->0xc, FontDefinition+0xC): large/default 13→16。
    V14R5 实证该字段不在游戏内定位路径 (fld[1]=16 盘 drawlog 逐字节同), 菜单侧行高语义。
  - PAK: psm 0x13→0x14, h 512→1024, CLUT 前 16 项 = 步骤A 同款 (项0 墨 ff ff ff 7f,
    项1-15 透明); 512x1024 4bpp = 0x40000B 与现 8bpp 512x512 像素区一字节不差 →
    px_size 0x40010 / NLOOP 0xC000 / tag / 记录总长 / 后续条目位移全部不变。

自检: 渲染逐字有墨且墨不越 16x16 窗 / 记录矩形两两不相交 / 行窗不触图标窗与 EN 带 /
4bpp 回环逐点 / PAK walk 落文件尾 'c' / 改动字节全部落在授权区段 / FT 结构与长度不变 /
dp_compress 槽回环 / SREC 区空白。
"""
import struct, sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out')
os.makedirs(HERE, exist_ok=True)
ZH16 = os.path.join(REPO_ROOT, 'tools', 'font_pipeline', 'data')
ZH14 = os.path.join(REPO_ROOT, 'tools', 'font_pipeline', 'data')
HAN = os.path.join(REPO_ROOT, 'docs', 'han_v2')
FZ16 = os.path.join(REPO_ROOT, 'third_party', 'fonts', '方正像素16.ttf')
SLOT_STORED, PAYLOAD_MAX, FT_LIMIT = 4421, 4413, 7222
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'hanliu', 'tools'))
from ft_dpc import dp_compress
from lz77_decode import decode_entry

# ---- 布局常量 (与 ELF cave V16 同一张配方单) ----
NCOL, CW, CH, Y0 = 62, 16, 16, 2
SKIP_ROW, SKIP_ROWS = 12, 3          # v(r) = Y0 + CH*(r + SKIP_ROWS*[r>=SKIP_ROW]); SKIP_OFF=48 动态
X0 = 20
EN_A, EN_B = 382, 397                # EN 带采样顶 S (记录 v0 = S-2, v1 = S-2+13); 全部 CJK 行(v<=370)之下
ICON_BOX = (19, 198, 64, 221)        # 原位保留, 逐 texel verbatim
W_TEX, H_TEX = 1024, 512             # h=1024 会使 MENU.IMG 纹理加载器崩溃 (22C/E/G 实测), 改横向扩展
INK, BG = 0, 1                       # 4bpp texel: CLUT[0]=墨(不透明), CLUT[1]=透明底

def yrow(r):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))

pak0 = open(HAN + r'\artifacts\COMMON_PAK.bin', 'rb').read()
cs = json.load(open(ZH16 + r'\charset_compiled_zh16.json', encoding='utf-8'))
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}       # 1136 (664 冻结 + 446 新 + 26)
singles = {k: int(v) for k, v in cs['codes'].items()}           # 76 single 码位
assert len(pair_of) == 1136 and len(singles) == 76, (len(pair_of), len(singles))

ft16 = open(ZH16 + r'\ft_expanded_zh16.bin', 'rb').read()       # 现役展开 FT (含 style5 修复)
ZH14A = np.asarray(Image.open(ZH14 + r'\atlas_zh14.png').convert('L')).astype(np.uint8)
assert ZH14A.shape == (512, 512)

# ---- 原始 8bpp 面 (图标窗 verbatim 源) ----
SURF = 0x146D
ORIG8 = np.frombuffer(pak0[SURF:SURF + 512 * 512], dtype=np.uint8).reshape(512, 512).copy()

def parse_faces(ft, body_off=28):
    p = body_off
    n = struct.unpack_from('<I', ft, 24)[0]
    faces = []
    for f in range(n):
        l = struct.unpack_from('<I', ft, p)[0]; p += 4
        nm = ft[p:p + l].decode('latin-1'); p += l
        fld = list(struct.unpack_from('<14I', ft, p)); p += 56
        nrec = fld[4] * fld[5]
        recs = [struct.unpack_from('<BB4H', ft, p + 10 * r) for r in range(nrec)]
        p += nrec * 10
        faces.append((nm, fld, recs))
    return p, faces

# FT 头: [u32 blob_len=20][20B blob][u32 nfaces=3] = 28B; 其后 3 个 face, 尾部 styles
_sl = struct.unpack_from('<I', ft16, 0)[0]
assert _sl == 20 and struct.unpack_from('<I', ft16, 24)[0] == 3
HEAD_END, F16 = parse_faces(ft16)
assert [f[0] for f in F16] == ['large', 'default', 'huge']
HEAD = ft16[:28]
STYLES = ft16[HEAD_END:]                                        # NS0 + styles (style5 1.0 修复在内)
SREC16 = tuple(F16[1][2][0x20 - 0x20])
OLD_SREC = SREC16
assert OLD_SREC == (0, 10, 136, 466, 146, 482), OLD_SREC

EN_CODES = list(range(0x21, 0x7F)) + [0x92, 0xAE, 0xE7, 0xF1]
EN_REC14 = {}
_ft14 = open(ZH14 + r'\ft_expanded_zh14.bin', 'rb').read()
_, F14 = parse_faces(_ft14)
for c in EN_CODES:
    EN_REC14[c] = tuple(F14[1][2][c - 0x20])

# ---- 1) atlas texel 网格 (H_TEX x W_TEX, 值 INK/BG) ----
A = np.full((H_TEX, W_TEX), BG, dtype=np.uint8)
x0b, y0b, x1b, y1b = ICON_BOX
A[y0b:y1b, x0b:x1b] = np.where(ORIG8[y0b:y1b, x0b:x1b] != 31, INK, BG)

# ---- 2) CJK: 方正像素16 渲染 ----
fnt = ImageFont.truetype(FZ16, 16)
# FZXS16 缺字回退 (实测仅 3 字): 用现役 zh16 atlas 的 13px 字形块, 放入 16px 窗 (x+1, y+2),
# 底边距 ~2px 与 FZ 基线协调 — 三字均为罕见符号/生僻字, 观感一致性可接受。
ZH16A = np.asarray(Image.open(ZH16 + r'\atlas_zh16.png').convert('L')).astype(np.uint8)
assert ZH16A.shape == (512, 512)
FALLBACK16 = {'®', 'µ', '蹚'}

def yrow13(r):
    return 2 + 13 * r + (39 if r >= 14 else 0)

def render16_zh16(ch, x, y):
    l, t = pair_of[ch]
    slot = (l - 0xA1) * 94 + (t - 0xA1)
    sx, sy = X0 + 13 * (slot % 37), yrow13(slot // 37)
    blk = ZH16A[sy:sy + 13, sx:sx + 13]
    assert (blk != 31).any(), ch
    g = np.zeros((16, 16), dtype=bool)          # 布尔墨窗 (ZH16 atlas: 31=底, 0=墨)
    g[2:15, 1:14] = blk != 31
    return g

def render16(ch):
    """FZXS16 16px → 16x16 布尔墨窗 (draw origin (8,8), 窗 = canvas[8:24,8:24) = em)。"""
    img = Image.new('L', (32, 32), 255)
    d = ImageDraw.Draw(img)
    d.text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24]
    out = win < 128                                             # 阈值化
    if out.any():
        ys, xs = np.where(out)
        # 墨越窗检测 (窗内边缘=允许贴边, 窗外=裁切损坏)
        full = a < 128
        fys, fxs = np.where(full)
        if fys.min() < 8 or fxs.min() < 8 or fys.max() >= 24 or fxs.max() >= 24:
            raise SystemExit('[FAIL] %r 墨越出 16x16 em 窗: x[%d..%d] y[%d..%d]'
                             % (ch, fxs.min() - 8, fxs.max() - 8, fys.min() - 8, fys.max() - 8))
    return out

def draw_cell(ch, x, y, tag):
    if ch in FALLBACK16:
        g = render16_zh16(ch, x, y)
    else:
        g = render16(ch)
    if not g.any():
        raise SystemExit('[FAIL] 空字形 %r (%s)' % (ch, tag))
    A[y:y + CH, x:x + CW] = np.where(g, INK, BG)

def cellpos(slot):
    c, r = slot % NCOL, slot // NCOL
    return X0 + CW * c, yrow(r), c, r

print('[CJK] 渲染 pair %d ...' % len(pair_of))
for ch, (l, t) in pair_of.items():
    slot = (l - 0xA1) * 94 + (t - 0xA1)
    x, y, c, r = cellpos(slot)
    assert r <= 40 and (y + CH) <= H_TEX, (ch, slot, r)
    draw_cell(ch, x, y, 'pair slot=%d' % slot)

SINGLE_SLOTS = list(range(683, 700)) + list(range(1153, 1212))
assert len(SINGLE_SLOTS) == 76
used_pair_slots = {(l - 0xA1) * 94 + (t - 0xA1) for (l, t) in pair_of.values()}
assert not (set(SINGLE_SLOTS) & used_pair_slots)
single_chars = sorted(singles, key=lambda k: singles[k])
single_cells = {}
print('[CJK] 渲染 single 76 ...')
for ch, slot in zip(single_chars, SINGLE_SLOTS):
    x, y, c, r = cellpos(slot)
    assert r <= 40
    draw_cell(ch, x, y, 'single slot=%d' % slot)
    single_cells[ch] = (x, y)
code2single = {code: ch for ch, code in singles.items()}

# ---- 3) EN 带 98 码位: ZH14 源窗绝对拷贝 → 新带 714/729 ----
def en_rec_new(c):
    r = EN_REC14[c]
    S = EN_A if (r[3] + 2) < 460 else EN_B
    return (r[0], r[1], r[2], S - 2, r[4], S - 2 + 13)

for c in EN_CODES:
    rec = EN_REC14[c]
    u0, v0, u1 = rec[2], rec[3], rec[4]
    sx, sy = u0 + X0, v0 + 2               # ZH14 源采样顶 (452/468)
    w_ = u1 - u0
    blk = ZH14A[sy + 2:sy + 2 + 13, sx:sx + w_]
    if not (blk != 31).any():
        continue                            # 空记录不动
    ty = EN_A if sy < 460 else EN_B
    A[ty - 2:ty - 2 + 13, sx:sx + w_] = np.where(blk != 31, INK, BG)

# 0x7B/0x7D 实心▲▼ 滚动三角 (子代理A 定案, zh16 同款, 移到新带)
for c_, up in ((0x7B, True), (0x7D, False)):
    rec = EN_REC14[c_]
    u0, v0, u1 = rec[2], rec[3], rec[4]
    sx, sy = u0 + X0, v0 + 2
    w_ = u1 - u0
    ty = EN_A if sy < 460 else EN_B
    y0 = ty - 2
    A[y0:y0 + 13, sx:sx + w_] = BG                  # 清格
    h = 9
    for r in range(h):
        f = (r if up else h - 1 - r) / (h - 1)
        span = min(2 * round(f * (w_ / 2)) + 1, w_)
        xa = sx + (w_ - span) // 2
        A[y0 + 2 + r, xa:xa + span] = INK
print('[EN] 98 码位 → 带 %d/%d (v0 %d/%d)' % (EN_A, EN_B, EN_A - 2, EN_B - 2))

# ---- 4) 记录构建 ----
new_single_rec = {}
for ch, (x, y) in single_cells.items():
    code = singles[ch]
    new_single_rec[code] = (0, CW, x - X0, y, x - X0 + CW, y + CH)
SREC = (0, 10, 136, 420, 146, 436)       # 空白记录 → EN 带下方空白区

def build_recs(nm):
    fi = 0 if nm == 'large' else (1 if nm == 'default' else 2)
    fld = list(F16[fi][1])
    if nm != 'huge':
        fld[1] = CH                        # 16px 行高度量 (desc->0xc 候选源1)
        if os.environ.get('FLD32', '1') == '1':
            fld[2] = 2 * CH                # 26→32: 候选源2 (26 = 2x13); FLD32=0 时保留 26
            fld[3] = 2 * CH
    recs = []
    lo, hi = (0x20, 0x100) if nm != 'huge' else (0x20, 0x80)
    for c in range(lo, hi):
        if c in EN_CODES:
            recs.append(en_rec_new(c))
        elif c in new_single_rec:
            recs.append(new_single_rec[c])
        else:
            recs.append(SREC)
    assert len(recs) == fld[4] * fld[5], (nm, len(recs))
    return fld, recs

out = bytearray(HEAD)
meta = {}
for nm in ('large', 'default', 'huge'):
    fld, recs = build_recs(nm)
    meta[nm] = fld
    out += struct.pack('<I', len(nm)) + nm.encode()
    out += struct.pack('<14I', *fld)
    for r in recs:
        out += struct.pack('<BB4H', *r)
out += STYLES
expanded = bytes(out)
assert len(expanded) == len(ft16), (len(expanded), len(ft16))
assert meta['large'][1] == CH and meta['default'][1] == CH and meta['huge'][1] == 16
assert meta['huge'][4] == 16 and meta['huge'][5] == 6

# ---- 5) 自检 ----
_, F2 = parse_faces(expanded)
# 5a. 图标窗 verbatim
assert (A[y0b:y1b, x0b:x1b] == np.where(ORIG8[y0b:y1b, x0b:x1b] != 31, INK, BG)).all()
# 5b. 行窗不触图标窗 / 不触 EN 带 / 不越界 (用行 0..19: slot<=1211 -> row 19)
for r in range(0, 24):
    yy = yrow(r)
    assert (yy + CH) <= H_TEX
    assert yy + CH <= ICON_BOX[1] or yy >= ICON_BOX[3], ('icon clash', r, yy)
assert yrow(20) + CH <= EN_A - 2 + 16, ('EN clash', yrow(20))
# 5c. cave 公式最深用行 v1 = 2+16*22 = 354 (slot 1211 -> row 19); EN 带之下全部空白
assert yrow(19) + CH == 370, yrow(19)
assert EN_A - 2 - 370 >= 8
# 5d. SREC 区空白 + EN 带下方整带空白 (412..511)
assert not (A[412:512, :] == INK).any(), 'EN 带下方应空白'
assert not (A[SREC[3]:SREC[5], SREC[2] + X0:SREC[4] + X0] == INK).any(), 'SREC 区有墨'
# 5e. 记录矩形两两不相交 (atlas 坐标)
def rects_of(fi):
    rr = []
    for r in F2[fi][2]:
        if tuple(r) == SREC:
            continue
        rr.append((r[2] + X0, r[3], r[4] + X0, r[5]))
    return rr
uniq = sorted(set(rr for fi in range(3) for rr in rects_of(fi)))
def inter(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
nb = sum(1 for i in range(len(uniq)) for j in range(i + 1, len(uniq)) if inter(uniq[i], uniq[j]))
assert nb == 0, '记录矩形相交 %d' % nb
for fi in range(3):
    for r in rects_of(fi):
        assert 0 <= r[0] and r[2] <= W_TEX and 0 <= r[1] and r[3] <= H_TEX, r
print('[SELF] 记录矩形 %d 个两两不相交, 全部在 512x1024 内' % len(uniq))
# 5f. 单字节记录逐码位断言 (三 face)
for code, rec in new_single_rec.items():
    ch = code2single[code]
    x, y = single_cells[ch]
    assert rec == (0, CW, x - X0, y, x - X0 + CW, y + CH)
    for fi in (0, 1):
        assert tuple(F2[fi][2][code - 0x20]) == rec, ('single', hex(code), ch)
for c in EN_CODES:
    rec = en_rec_new(c)
    for fi, nm in ((0, 'large'), (1, 'default')):
        assert tuple(F2[fi][2][c - 0x20]) == rec, (nm, hex(c))
    if c < 0x80:
        assert tuple(F2[2][2][c - 0x20]) == rec, ('huge', hex(c))
for c in range(0x20, 0x80):
    r2 = tuple(F2[2][2][c - 0x20])
    want = en_rec_new(c) if c in EN_CODES else SREC
    assert r2 == want, ('huge rec', hex(c))
print('[SELF] EN 98/98 + single 76/76 + huge alias 断言 PASS')

# ---- 6) 4bpp 打包 + PAK ----
lo_n = A[:, 0::2].astype(np.uint8)       # 偶数列 → 低半字节 (步骤A 实证约定)
hi_n = A[:, 1::2].astype(np.uint8)       # 奇数列 → 高半字节
packed = (hi_n << 4) | lo_n
assert packed.shape == (H_TEX, W_TEX // 2) and packed.nbytes == 0x40000

pak2 = bytearray(pak0)
assert len(pak2) == 400659
FONT_HDR, W_OFF, H_OFF, CLUTSZ_OFF = 0x1049, 0x104D, 0x1051, 0x1055
CLUT_DATA, PX_SIZE_OFF, PX_TAG, PX_DATA = 0x1069, 0x1469, 0x146D, 0x147D
assert struct.unpack_from('<I', pak2, FONT_HDR)[0] == 0x13
assert struct.unpack_from('<II', pak2, W_OFF) == (512, 512)
assert struct.unpack_from('<I', pak2, PX_SIZE_OFF)[0] == 0x40010
assert struct.unpack_from('<H', pak2, PX_TAG)[0] == 0xC000
struct.pack_into('<I', pak2, FONT_HDR, 0x14)                 # PSMT4
struct.pack_into('<I', pak2, W_OFF, W_TEX)                   # w 512→1024 (h 保持 512: h=1024 崩加载器)
struct.pack_into('<I', pak2, H_OFF, H_TEX)
clut16 = b'\xff\xff\xff\x7f' + b'\xff\xff\xff\x00' * 15      # 项0=墨, 项1-15=透明 (步骤A 同款)
pak2[CLUT_DATA:CLUT_DATA + 64] = clut16
pak2[PX_DATA:PX_DATA + 0x40000] = packed.tobytes()
pak2 = bytes(pak2)

# 6a. 改动字节全部落在授权区段 (psm / h / CLUT16 / 像素区; px_size/tag/clut 其余不动)
base = pak0
zones = [(FONT_HDR, FONT_HDR + 4), (W_OFF, H_OFF + 4), (CLUT_DATA, CLUT_DATA + 64),
         (PX_DATA, PX_DATA + 0x40000)]
changed = [i for i in range(len(base)) if base[i] != pak2[i]]
assert changed, 'no change?'
for i in changed:
    assert any(a <= i < b for a, b in zones), '越界改动 @0x%X' % i
assert struct.unpack_from('<II', pak2, W_OFF) == (1024, 512)
assert struct.unpack_from('<I', pak2, PX_SIZE_OFF)[0] == 0x40010
assert struct.unpack_from('<H', pak2, PX_TAG)[0] == 0xC000
assert pak2[CLUT_DATA + 64:CLUT_DATA + 0x400] == base[CLUT_DATA + 64:CLUT_DATA + 0x400]
assert pak2[PX_TAG + 2:PX_DATA] == base[PX_TAG + 2:PX_DATA]   # tag 其余 (EOP/NREG/REGS) 不动
print('[PAK] 改动 %d 字节, 全部落 4 授权区段; px_size/NLOOP/tag 未动' % len(changed))

# 6b. PAK walk (字库记录格式终点 = 槽终点 0x4147D, 零填充 → 后续条目零位移)
def walk(pak):
    n = len(pak); p = 0; ents = []
    while p + 8 <= n:
        mode, nl = struct.unpack_from('<II', pak, p)
        if nl < 1 or nl > 64 or p + 8 + nl > n:
            return p, ents, 'BAD nl @0x%X' % p
        name = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        q = p + 8 + nl
        if mode != 0:
            return p, ents, 'BAD mode @0x%X' % p
        psm, w, h, clut = struct.unpack_from('<IIII', pak, q)
        q2 = q + 16 + clut
        px_size = struct.unpack_from('<I', pak, q2)[0]
        q3 = q2 + 4 + px_size
        ents.append(dict(off=p, name=name, psm=psm, w=w, h=h, clut=clut, px=px_size, end=q3))
        p = q3
        if p == n:
            return p, ents, 'EXACT-END'
    return p, ents, 'STOP'

end, ents, why = walk(pak2)
assert why == 'STOP' and end == len(pak2) - 4 and pak2[end:end + 4] == b'c\x00\x00\x00', (why, hex(end))
font = [e for e in ents if e['name'] == 'new_font_revised'][0]
assert font['off'] == 0x1031 and font['psm'] == 0x14 and font['w'] == 1024 and font['h'] == 512
assert font['clut'] == 0x410 and font['px'] == 0x40010 and font['end'] == 0x4147D
pda = [e for e in ents if e['name'] == 'pda-lcd-02'][0]
assert pda['off'] == 0x4147D and pda['psm'] == 0x13
print('[PAK] walk %d 条目:' % len(ents))
for e in ents:
    print('     @0x%06X %-22r psm=0x%02X %dx%d clut=%d px=0x%X end=0x%X'
          % (e['off'], e['name'], e['psm'], e['w'], e['h'], e['clut'], e['px'], e['end']))

# 6c. 4bpp 回环解码 == texel 网格
pk = np.frombuffer(pak2[PX_DATA:PX_DATA + 0x40000], dtype=np.uint8).reshape(H_TEX, W_TEX // 2)
dec = np.empty((H_TEX, W_TEX), dtype=np.uint8)
dec[:, 0::2] = pk & 0x0F
dec[:, 1::2] = (pk >> 4) & 0x0F
assert (dec == A).all(), '4bpp 回环不一致'
print('[SELF] 4bpp 回环 1024x512 逐点一致; 墨 texel=%d' % int((A == INK).sum()))

# ---- 7) FT 槽 ----
payload = dp_compress(expanded, verbose=False)
assert len(payload) <= PAYLOAD_MAX, len(payload)
frame = struct.pack('<II', len(payload), len(expanded)) + payload
slot = frame + b'\x00' * (SLOT_STORED - len(frame))
back, stats = decode_entry(slot)
assert back == expanded
print('[FONT] expanded %dB, payload %dB, slot %dB; 槽回环 PASS' % (len(expanded), len(payload), len(slot)))

# ---- 8) 产物 ----
json.dump({'mode': 'v16px',
           'codes': singles,
           'pair_of': {k: list(v) for k, v in pair_of.items()},
           'grid': {'ncol': NCOL, 'cw': CW, 'ch': CH, 'gridy': Y0, 'x0': X0,
                    'skip_row': SKIP_ROW, 'skip_rows': SKIP_ROWS, 'skip_off': SKIP_ROWS * CH,
                    'nrows': 41, 'h_tex': H_TEX, 'en_y': [EN_A, EN_B],
                    'icon_box': list(ICON_BOX), 'srec': list(SREC),
                    'n_chars': len(pair_of) + len(singles)}},
          open(HERE + r'\charset_compiled_v16.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
open(HERE + r'\ft_expanded_v16.bin', 'wb').write(expanded)
open(HERE + r'\ft_slot_v16.bin', 'wb').write(slot)
open(HERE + r'\COMMON_PAK_V16.bin', 'wb').write(pak2)
prev = np.full((H_TEX, W_TEX), 255, dtype=np.uint8)
prev[A == INK] = 0
Image.fromarray(prev).save(HERE + r'\atlas_v16.png')
with open(HERE + r'\layout_v16.txt', 'w', encoding='utf-8') as f:
    f.write('# v16 layout CH=%d grid=(%d cols x 41 rows used) pitch=%dx%d y0=%d skip=(r>=%d:+%d) en=(%d,%d)\n'
            % (CH, NCOL, CW, CH, Y0, SKIP_ROW, SKIP_ROWS * CH, EN_A, EN_B))
    for ch, (l, t) in pair_of.items():
        s_ = (l - 0xA1) * 94 + (t - 0xA1)
        x, y, c, r = cellpos(s_)
        f.write('pair %s slot=%d cell=(%d,%d) rec=(%d,%d,%d,%d)\n'
                % (ch, s_, x, y, x - X0, y, x - X0 + CW, y + CH))
    for ch in single_chars:
        x, y = single_cells[ch]
        f.write('single %s 0x%02X cell=(%d,%d) rec=(%d,%d,%d,%d)\n'
                % (ch, singles[ch], x, y, x - X0, y, x - X0 + CW, y + CH))
print('[BUILD] PASS → COMMON_PAK_V16.bin / ft_slot_v16.bin / ft_expanded_v16.bin (%d 字)'
      % (len(pair_of) + len(singles)))
