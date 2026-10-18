# -*- coding: utf-8 -*-
r"""verify_atlas_rows.py — 独立复核 H=608 的依据：逐行统计图集墨占用

判据来源(空位任务): row 25/26（EN 带 v=452/468）与 **row 27（键盘带 v=482/498）** 都被占
⇒ 可用行 = {0..24} ∪ {28..}，据此 H=608 才有 418 空闲格。
本脚本: 直接读图集数组（构建任务解出的 1024×512），按 cave 的行公式算每行的墨量，独立核对。
"""
import os
import sys

import numpy as np

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

Y0, CW, CH, NCOL, SKIP_ROW, SKIP_ROWS = 2, 16, 16, 62, 12, 3
W = 1024
INK = 0  # 实测: 墨 = nibble 0x0


def row_y(r):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))


for fn in ('atlas_engine_authoritative.npy', 'atlas_engine.npy'):
    p = os.path.join(R81, fn)
    if not os.path.exists(p):
        continue
    a = np.load(p, allow_pickle=False)
    print('=' * 78)
    print('%s  shape=%s dtype=%s' % (fn, a.shape, a.dtype))
    if a.ndim != 2:
        print('  (非 2 维，跳过)')
        continue
    H, Wd = a.shape
    tot_ink = int((a == INK).sum())
    print('  尺寸 %dx%d ; 墨像素(==%d) 合计 %d' % (Wd, H, INK, tot_ink))
    print()
    print('  逐行统计（行公式 y = %d + %d*(r + %d*[r>=%d])）:' % (Y0, CH, SKIP_ROWS, SKIP_ROW))
    print('    r    y    墨量    判定')
    for r in range(0, 40):
        y = row_y(r)
        if y + CH > H:
            break
        band = a[y:y + CH, :]
        ink = int((band == INK).sum())
        tag = ''
        if r in (25, 26):
            tag = '← EN 带 (v=452/468)'
        elif r == 27:
            tag = '← ★ 键盘带 (v=482/498)'
        elif ink > 0:
            tag = '← 有墨'
        print('    %-3d  %-4d  %-7d %s' % (r, y, ink, tag))
    print()
    # 汇总: 哪些行"有墨"（阈值取 50 texel，避免抗锯齿噪点误判）
    used = [r for r in range(0, 40) if row_y(r) + CH <= H and int((a[row_y(r):row_y(r) + CH] == INK).sum()) > 50]
    print('  有墨的行（>50 texel）: %s' % used)
    print('  ⇒ 空行: %s' % [r for r in range(0, 40) if row_y(r) + CH <= H and r not in used])
    free = [r for r in range(0, 40) if row_y(r) + CH <= H and r not in used]
    print()
    print('  ★ 若新增行从 row %d 起，可用格 = %d 行 × %d 列 = **%d 格**'
          % (max(used) + 1 if used else 0, len([r for r in free if r > (max(used) if used else -1)]),
             NCOL, len([r for r in free if r > (max(used) if used else -1)]) * NCOL))
    print()
