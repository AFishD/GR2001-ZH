# -*- coding: utf-8 -*-
r"""p7_capacity.py — 字库容量的**逐格**账本 (只读 GR_ZH109)。

对每个"lead 区间假说"给出:
  · 可寻址对偶 slot 数;             · 现役已用;
  · 其中**物理可用**的空白干净格;   · 被墨/被 FT 记录矩形压住而不可用的;
再单独算单字节码带的空码位为什么不能用。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0
rect = np.zeros((H, W), dtype=bool)
for (_nm, _fld, recs) in faces:
    for r in recs:
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True

cs = tcslib.Charset()
used = set(tcslib.pair_slot(*p) for p in cs.enc_pair.values())
print('现役 charset: 对偶 %d (slot %d..%d) + 单字节 %d'
      % (len(cs.enc_pair), min(used), max(used), len(cs.enc_single)))


def audit(lead_hi_excl, name):
    slots = []
    for lead in range(0xA1, lead_hi_excl):
        for trail in range(0xA1, 0xFF):
            slots.append(tcslib.pair_slot(lead, trail))
    n_used = n_free = n_ink = n_rec = n_conf = n_oob = 0
    for slot in slots:
        if slot in used:
            n_used += 1
            continue
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        if x + 16 > W or y + 16 > H:
            n_oob += 1
            continue
        if tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((row, col)):
            n_conf += 1
            continue
        c = ink[y:y + 16, x:x + 16]
        r = rect[y:y + 16, x:x + 16]
        if c.any():
            n_ink += 1
        elif r.any():
            n_rec += 1
        else:
            n_free += 1
    print('\n[%s] lead 0xA1..0x%02X ⇒ 可寻址对偶 slot %d'
          % (name, lead_hi_excl - 1, len(slots)))
    print('   已用 %d | ★物理可用(零墨且无记录矩形) %d | 有墨(旧残墨) %d | 被FT记录压 %d'
          ' | 采样窗冲突 %d | 越界 %d'
          % (n_used, n_free, n_ink, n_rec, n_conf, n_oob))
    print('   ⇒ 还能加 %d 个汉字 (现役 1175 + %d = %d)' % (n_free, n_free, 1175 + n_free))
    return n_free


a = audit(0xAE, '假说 B: lead ≤ 0xAD')
b = audit(0xB1, '现役 gate: lead ≤ 0xB0 (sltiu 0xB1)')
c = audit(0xB4, '假说 A: lead ≤ 0xB3 (gate 再抬到 0xB4)')
print('\n图集网格上限 = 62 列 × 28 行 = 1736 格; 单张 1024x512 贴图最多容纳 1736 个 16x16 字形。')

# ---- 单字节码带 ----
print('\n单字节码带 0x80..0xFF:')
free_single = [b for b in range(0x80, 0x100) if b not in cs.codes]
print('  现役 %d 个; 空着 %d 个 = %s'
      % (len(cs.codes), len(free_single), ' '.join('%02X' % b for b in free_single)))
icons = {0xB1: '△ 三角键 (引擎硬编码图标码)', 0xB5: '✕ 叉键 (引擎硬编码图标码)'}
for b in free_single:
    if 0xA1 <= b <= 0xB0:
        why = '引擎的对偶 **lead** 区间 0xA1..0xB0 ⇒ 写它出去会吞掉后一个字'
    elif b in icons:
        why = icons[b]
    else:
        why = '?'
    print('    0x%02X  %s' % (b, why))
