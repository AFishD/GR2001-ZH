# -*- coding: utf-8 -*-
r"""zx_icon.py — 只读: △/✕ 图标像素来源诊断 (决定新格里的图标字形从哪来)

  [1] 图集里 rec[145]/rec[149] 指向的窗口 (484,215)-(494,231) 到底是什么
  [2] pda_counterparts (PSMT8 256x256 + CLUT 0x410) 里硬编码 UV (25,198)-(45,218) / (1,198)-(21,218)
      —— 按 CLUT alpha 取形状, 并 20x20 → 16x16 归一, 打印 ASCII 供肉眼判定
"""
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                   # noqa: E402
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
OUT = zx_lib.OUT
os.makedirs(OUT, exist_ok=True)
LS = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LS.append(s)


def show(bm, label):
    P('  %s (墨 %d/%d)' % (label, int(bm.sum()), bm.size))
    for r in bm:
        P('     ' + ''.join('#' if v else '.' for v in r))


iso = tcslib.Iso(ISO)
ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
pak_e = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
recs = tcslib.parse_pak_records(pak)
P('COMMON.PAK 记录: %s' % [(r[0], hex(r[1]), r[2], r[3], hex(r[5])) for r in recs])

P('')
P('=' * 78)
P('[1] 图集 rec[145]/rec[149] 窗口 (484,215)-(494,231)')
P('=' * 78)
_nm, psm, w, h, clut, px, PX = recs[1]
img, cov = zx_lib.decode_engine(pak[PX:PX + px], 1024, 512)
for (u0, v0, u1, v1, tag) in ((480, 213, 490, 229, 'rec[145]=0xB1/△'),
                              (480, 213, 490, 229, 'rec[149]=0xB5/✕')):
    win = img[v0 + 2:v1 + 2, u0 + 4:u1 + 4]
    show(win, '%s 采样窗 (+4,+2) = (%d,%d)-(%d,%d)' % (tag, u0 + 4, v0 + 2, u1 + 4, v1 + 2))

P('')
P('=' * 78)
P('[2] pda_counterparts (PSMT8 256x256, clut=0x410)')
P('=' * 78)
_nm2, psm2, w2, h2, clut2, px2, PX2 = recs[3]
P('  rec#3 %s psm=0x%02X %dx%d clut=0x%X px=0x%X px_off=0x%X' % (_nm2, psm2, w2, h2, clut2, px2, PX2))
clut_off = PX2 - clut2
clut_bytes = pak[clut_off:clut_off + clut2]
P('  CLUT 前 32 B: %s' % ' '.join('%02X' % b for b in clut_bytes[:32]))
P('  CLUT 后 16 B: %s' % ' '.join('%02X' % b for b in clut_bytes[-16:]))
pal_bytes = clut_bytes[16:16 + 256 * 4]
assert len(pal_bytes) == 1024, len(pal_bytes)
pal = np.frombuffer(pal_bytes, dtype=np.uint8).reshape(256, 4)
P('  CLUT[16:16+1024] 当 256xRGBA: alpha 直方图 %s'
  % [(int(v), int((pal[:, 3] == v).sum())) for v in sorted(set(pal[:, 3].tolist()))][:8])
surf = np.frombuffer(pak[PX2:PX2 + (w2 * h2)], dtype=np.uint8).reshape(h2, w2)
for (u0, v0, u1, v1, tag) in ((25, 198, 45, 218, '△ 硬编码 UV'), (1, 198, 21, 218, '✕ 硬编码 UV')):
    reg = surf[v0:v1, u0:u1]
    alpha = pal[reg, 3]
    P('  %s (%d,%d)-(%d,%d): 索引种类 %d, alpha 种类 %d, alpha>=128 的像素 %d/%d'
      % (tag, u0, v0, u1, v1, len(set(reg.flatten().tolist())), len(set(alpha.flatten().tolist())),
         int((alpha >= 128).sum()), alpha.size))
    bm = alpha >= 64
    if bm.any():
        show(bm, '%s (alpha>=64)' % tag)
        # 20x20 -> 16x16 (面积平均 >= 0.5 为墨)
        ih, iw = bm.shape
        out = np.zeros((16, 16), dtype=bool)
        for y in range(16):
            for x in range(16):
                y0 = y * ih // 16
                y1 = max(y0 + 1, (y + 1) * ih // 16)
                x0 = x * iw // 16
                x1 = max(x0 + 1, (x + 1) * iw // 16)
                out[y, x] = bm[y0:y1, x0:x1].mean() >= 0.5
        show(out, '%s → 16x16 (面积平均>=0.5)' % tag)
        P('      hex: %s' % ['%04X' % int(''.join('1' if v else '0' for v in out[y]), 2)
                             for y in range(16)])
    # 彩色版: 直接用 alpha 阈值 (>=64)
    bm2 = alpha >= 64
    P('  %s alpha>=64 墨 %d/%d' % (tag, int(bm2.sum()), bm2.size))
    # ★ 索引图 + 调色板各候选口径 (判定 alpha 到底是哪一位)
    P('  索引图 (十六进制两位):')
    for y in range(v1 - v0):
        P('     ' + ' '.join('%02X' % v for v in reg[y]))
    idxs = sorted(set(reg.flatten().tolist()))
    P('  出现的索引 %d 个: %s' % (len(idxs), idxs[:24]))
    for base in (0, 4, 8, 12, 16):
        words = [struct.unpack_from('<I', clut_bytes, base + 4 * i)[0] for i in idxs]
        a3 = [(w >> 24) & 0xFF for w in words]
        a15 = [(w >> 15) & 1 for w in words]
        a31 = [(w >> 31) & 1 for w in words]
        P('    base=%-3d alpha(byte3) 直方图 %s' % (base, sorted(set(a3))))
        P('            bit15 直方图 %s ; bit31 直方图 %s'
          % (sorted(set(a15)), sorted(set(a31))))
        if base == 16 and len(set(a15)) == 2 and 0 in a15 and 1 in a15:
            m = np.zeros(reg.shape, dtype=bool)
            lut = {i: ((struct.unpack_from('<I', clut_bytes, 16 + 4 * i)[0] >> 15) & 1)
                   for i in idxs}
            for y in range(reg.shape[0]):
                for x in range(reg.shape[1]):
                    m[y, x] = bool(lut[reg[y, x]])
            show(m, '%s bit15==1 (base16)' % tag)
            m2 = ~m
            show(m2, '%s bit15==0 (base16)' % tag)
    if tag.startswith('△'):
        np.save(os.path.join(OUT, 'icon_triangle_20x20.npy'), bm2)

iso.close()
with open(os.path.join(OUT, 'icon.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(LS) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'icon.txt'))
