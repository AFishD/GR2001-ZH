# -*- coding: utf-8 -*-
r"""lead_ownership.py — 像素归属分析: 每个槽位的墨到底是"活字形"还是"可回收的旧字"

要回答用户三个问题:
  ① 90 个"需回收"槽位里的墨, 到底是谁的? (FT 记录指向的活字形? 还是没人要的旧字?)
  ② 上下箭头(0x7B/0x7D)与 ç/ñ(0xE7/0xF1) 为什么被标成"需回收"? (答: 分类错了)
  ③ 那个"蓝框盖在四个绿框中间"的是什么? (答: 空格 0x20 的记录矩形, 它本来就是空的)
     —— 但要顺带查: 有没有 FT 记录矩形**压在在用格上**(会互相干扰)?
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

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH102', 'GR_ZH102.iso')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
code2ch = {int(v): k for k, v in cs['codes'].items()}

slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        slot_of[tcslib.pair_slot(b1, b2)] = ch

# 每个 code 的 FT 记录矩形 (取 large 面; 各 face 基本一致)
rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
rect_of = {}
for idx, r in enumerate(rec):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 > u0 and v1 > v0:
        rect_of[idx + 0x20] = (u0, v0, u1, v1)

# 需要 / 不需要 的 code
need_codes = set(code2ch) | set(range(0x20, 0x7F))          # 我们的单字节 + 全部可打印 ASCII
ARROWS = {0x7B, 0x7D}                                        # 引擎滚动箭头 (硬编码)
print('单字节码 %d 个 (含 ç/ñ); ASCII 0x20..0x7E; 箭头 %s' % (len(code2ch), sorted(hex(x) for x in ARROWS)))
print('FT 记录 %d 条: 其中 code 属于"我们要的" %d 条, 不属于的 %d 条'
      % (len(rect_of), sum(1 for c in rect_of if c in need_codes),
         sum(1 for c in rect_of if c not in need_codes)))
print()

# ── ① 90 个"需回收"槽位: 墨归谁 ─────────────────────────────────────
print('=' * 78)
print('① 未用槽位里"有墨"的 90 个: 墨到底归谁')
print('=' * 78)
kinds = {}
detail = []
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
    # 这块墨被哪些 FT 记录覆盖
    cover = []
    for code, (u0, v0, u1, v1) in rect_of.items():
        ov = np.zeros((16, 16), dtype=bool)
        X0, Y0 = max(x, u0), max(y, v0)
        X1, Y1 = min(x + 16, u1), min(y + 16, v1)
        if X1 > X0 and Y1 > Y0:
            ov[Y0 - y:Y1 - y, X0 - x:X1 - x] = True
            m = int((cell & ov).sum())
            if m:
                cover.append((code, m, code in need_codes or code in ARROWS))
    live = sum(m for _c, m, ok in cover if ok)
    deadink = n - live
    key = ('live_ft' if live and not deadink else
           'residue' if not live else 'mixed')
    kinds[key] = kinds.get(key, 0) + 1
    detail.append((slot, slot // 62, slot % 62, x, y, n, live, deadink,
                   [(('0x%02X' % c), m) for c, m, _o in cover]))
print('  分类: live_ft(墨全是活字形) %d ; mixed(部分活+部分残) %d ; residue(全是残) %d'
      % (kinds.get('live_ft', 0), kinds.get('mixed', 0), kinds.get('residue', 0)))
print()
print('  明细 (前 24):')
for slot, row, col, x, y, n, live, dk, cov in sorted(detail, key=lambda t: -t[5])[:24]:
    print('    slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 墨%3d = 活%3d + 残%3d  覆盖记录: %s'
          % (slot, row, col, x, y, n, live, dk, ', '.join('%s:%d' % c for c in cov[:4])))

# ── ② 箭头 / çñ 被误标 ────────────────────────────────────────────
print()
print('=' * 78)
print('② 箭头 0x7B/0x7D 与 ç/ñ 0xE7/0xF1: 它们的记录矩形压在哪些槽位上')
print('=' * 78)
for code in (0x7B, 0x7D, 0xE7, 0xF1):
    u0, v0, u1, v1 = rect_of[code]
    hit = []
    for slot in range(1504):
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        if x < u1 and x + 16 > u0 and y < v1 and y + 16 > v0:
            st = '在用' if slot in slot_of else '空'
            hit.append('slot%d(row%d,col%d,%s)' % (slot, slot // 62, slot % 62, st))
    print('  0x%02X rec=(%d,%d,%d,%d) 墨%d px  压到槽位: %s'
          % (code, u0, v0, u1, v1, int(ink[v0:v1, u0:u1].sum()), ' '.join(hit) or '无'))

# ── ③ FT 记录矩形压在"在用格"上的冲突 ──────────────────────────────
print()
print('=' * 78)
print('③ 冲突检查: FT 记录矩形 vs 在用对偶格 (会互相干扰)')
print('=' * 78)
used_mask = np.zeros((H, W), dtype=bool)
for slot in slot_of:
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    used_mask[y:y + 16, x:x + 16] = True
conf = []
for code, (u0, v0, u1, v1) in sorted(rect_of.items()):
    ov = used_mask[v0:v1, u0:u1]
    m = int(ov.sum())
    if m:
        inkhere = int(ink[v0:v1, u0:u1].sum())
        ch = code2ch.get(code, chr(code) if 0x20 <= code < 0x7F else '?')
        conf.append((code, ch, u0, v0, u1, v1, m, inkhere))
print('  有 %d 条 FT 记录的矩形**压在在用格上**:' % len(conf))
for code, ch, u0, v0, u1, v1, m, ih in conf[:20]:
    print('    0x%02X %-3s rec=(%4d,%3d,%4d,%4d) 压住在用格 %3d px; 该矩形内墨 %d px'
          % (code, ch, u0, v0, u1, v1, m, ih))
