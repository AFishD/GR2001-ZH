# -*- coding: utf-8 -*-
"""r75_verify_l1mini.py -- verify the h=576/h=640 claims in the report (rows, px_size, +0x30)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import importlib.util
spec = importlib.util.spec_from_file_location(
    'capg', os.path.join(REPO, 'tools', 're', 'toolbelt', 'cap_grid.py'))
# cap_grid runs main() at import -> instead re-implement the two helpers here (3 lines each)
EN_BAND = (452, 468)


def yrow(r, Y0, CH, SR, SN):
    return Y0 + CH * (r + (SN if r >= SR else 0))


def eval_cfg(H, CW, CH, Y0, SR, SN, NCOL, W=1024):
    rows, r = [], 0
    while True:
        y = yrow(r, Y0, CH, SR, SN)
        if y + CH > H:
            break
        rows.append((r, y))
        r += 1
    blocked = [r for (r, y) in rows if not (y + CH <= EN_BAND[0] or y >= EN_BAND[1])]
    usable = len(rows) - len(blocked)
    return dict(H=H, rows=len(rows), last_row=rows[-1][0], last_y=rows[-1][1],
                blocked=blocked, usable_rows=usable, NCOL=NCOL, cells=usable * NCOL,
                free_vs_1504=usable * NCOL - 1504)


def px_size(H, seg_rows=64, stride=512):
    nseg = -(-H // seg_rows)
    return nseg, nseg * 48 + H * stride + 16


def acct(W, P):
    B = (0x10000 // W) << 2
    u = B + 16
    c = -(-P // u)
    f30 = P - c * 16
    npk = -(-f30 // B)
    return dict(B=B, unit=u, c=c, f30=f30, f30_hex='0x%X' % f30, npackets=npk,
                delivered=f30 + 16 * npk, slack=c * u - P,
                short16=(B < (c * u - P) < u))


OLD_PX = 0x40010
print('== 贴图尺寸 / 记录增量 ==')
for H in (512, 576, 640, 768, 1024):
    nseg, P = px_size(H)
    a = acct(1024, P)
    print('h=%-5d seg=%-3d px_size=0x%06X (%8d)  growth=%+8d  0x%X  +0x30=0x%X npk=%-5d '
          'delivered=%d slack=%d short16=%s'
          % (H, nseg, P, P, P - OLD_PX, P - OLD_PX, a['f30'], a['npackets'],
             a['delivered'], a['slack'], a['short16']))

print()
print('== 网格行 / 可用格（CW=CH=16, Y0=2, NCOL=62, 跳行按 CH=16 的最小合法解 12+3）==')
for H in (512, 576, 640, 768, 1024):
    print('  h=%-5d %s' % (H, json.dumps(eval_cfg(H, 16, 16, 2, 12, 3, 62), ensure_ascii=False)))
print()
print('== 备用跳行 12+2（洞 [194,226) 也盖住图标窗 [198,222)）==')
for H in (512, 576, 640):
    print('  h=%-5d %s' % (H, json.dumps(eval_cfg(H, 16, 16, 2, 12, 2, 64), ensure_ascii=False)))
print()
print('== 改格距的两条候选（h=512 不变）==')
for (CW, CH, SR, SN, NCOL) in ((14, 16, 12, 3, 73), (15, 16, 13, 2, 68), (16, 15, 13, 2, 64),
                               (16, 16, 12, 2, 64), (13, 13, 15, 2, 78), (12, 12, 16, 3, 85)):
    print('  CW=%d CH=%d skip=%d+%d NCOL=%d -> %s'
          % (CW, CH, SR, SN, NCOL, json.dumps(eval_cfg(512, CW, CH, 2, SR, SN, NCOL),
                                              ensure_ascii=False)))
