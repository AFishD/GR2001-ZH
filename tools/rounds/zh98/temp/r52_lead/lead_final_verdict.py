# -*- coding: utf-8 -*-
r"""lead_final_verdict.py — 最终判定: 图集里每一处墨是"活的"还是"残留"

判定优先级:
  1) 落在**已用对偶格**里          -> 活 (对偶字字形)
  2) 落在**FT 记录矩形**里          -> 活 (单字节/ASCII/箭头/çñ 字形)
  3) 其它                            -> **残留, 可清**
再单独回答: 92 个"空格有墨"里, 有多少属于第 3 类。
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'GR_ZH101.iso')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))

used = np.zeros((H, W), dtype=bool)
slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
        continue
    slot = tcslib.pair_slot(b1, b2)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H:
        used[y:y + 16, x:x + 16] = True
        slot_of[slot] = ch

ftm = np.zeros((H, W), dtype=bool)
rects = []
for fname, _fld, rs in faces:
    for idx, r in enumerate(rs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            continue
        rects.append((fname, idx + 0x20, u0, v0, u1, v1))
        ftm[v0:v1, u0:u1] = True

live = used | ftm
resid = ink & ~live
print('墨 %d px = 已用对偶格内 %d + FT 记录内 %d + **残留 %d**'
      % (int(ink.sum()), int((ink & used).sum()), int((ink & ftm & ~used).sum()), int(resid.sum())))

print()
print('=' * 78)
print('★ 92 个"空格有墨"的对偶槽位: 逐个判定')
print('=' * 78)
n_live = n_resid = 0
resid_slots = []
for slot in range(1504):
    if slot in slot_of:
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    cell = ink[y:y + 16, x:x + 16]
    n = int(cell.sum())
    if n == 0:
        continue
    cov = ftm[y:y + 16, x:x + 16]
    live_n = int((cell & cov).sum())
    resid_n = int((cell & ~cov).sum())
    if resid_n:
        n_resid += 1
        resid_slots.append((slot, slot // 62, slot % 62, x, y, n, live_n, resid_n))
    else:
        n_live += 1
print('  **完全由 FT 记录解释**(合法单字节字形) %d 个' % n_live)
print('  **含残留墨** %d 个 (残留合计 %d px):' % (n_resid, sum(t[7] for t in resid_slots)))
for slot, row, col, x, y, n, ln, rn in sorted(resid_slots, key=lambda t: -t[7])[:30]:
    print('     slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 墨%3d = 记录内%3d + **残留%3d**'
          % (slot, row, col, x, y, n, ln, rn))

print()
print('=' * 78)
print('★ 残留墨团块清单 (全部, 按大小)')
print('=' * 78)
from collections import deque
seen = np.zeros_like(resid, dtype=bool)
blobs = []
ys, xs = np.nonzero(resid)
for sy, sx in zip(ys.tolist(), xs.tolist()):
    if seen[sy, sx]:
        continue
    q = deque([(sy, sx)]); seen[sy, sx] = True
    x0 = x1 = sx; y0 = y1 = sy; n = 0
    while q:
        yy, xx = q.popleft(); n += 1
        x0 = min(x0, xx); x1 = max(x1, xx); y0 = min(y0, yy); y1 = max(y1, yy)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = yy + dy, xx + dx
            if 0 <= ny < H and 0 <= nx < W and resid[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    blobs.append((x0, y0, x1, y1, n))
blobs.sort(key=lambda b: -b[4])
print('  团块 %d 个, 合计 %d px' % (len(blobs), int(resid.sum())))
for x0, y0, x1, y1, n in blobs[:25]:
    # 附近有什么记录?
    near = [('0x%02X' % c, r) for _f, c, u0, v0, u1, v1 in rects
            if u0 - 6 <= x0 <= u1 + 6 and v0 - 4 <= y0 <= v1 + 4]
    tag = ('; '.join('%s rec=(%d,%d,%d,%d)' % (c, r[0], r[1], r[2], r[3]) for c, r in near[:2])) or '(周围无记录)'
    print('  (%4d,%3d)-(%4d,%3d) %3dpx  邻近: %s' % (x0, y0, x1, y1, n, tag))

io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'temp', 'r52', 'residue_final.json'),
        'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
            ink=int(ink.sum()), used=int((ink & used).sum()), ft=int((ink & ftm & ~used).sum()),
            residue=int(resid.sum()), n_blobs=len(blobs),
            blobs=[dict(x0=b[0], y0=b[1], x1=b[2], y1=b[3], px=b[4]) for b in blobs],
            slots_with_residue=[dict(slot=s, row=r, col=c, x=x, y=y, ink=n, resid=rn)
                                for s, r, c, x, y, n, _l, rn in resid_slots]),
            ensure_ascii=False, indent=1))
print()
print('→ residue_final.json 已写出')
