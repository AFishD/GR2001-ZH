# -*- coding: utf-8 -*-
r"""r64_capacity.py — 算清"还能扩多少字"

引擎地址: slot=(lead-0xA1)*94+(trail-0xA1); row=slot//62; col=slot%62;
          x=16*col; y=2+16*(row+3*(row>=12))
图集 1024x512 ⇒ y+16<=512 ⇒ row<=27 (y=482..498) ⇒ 最多 28 行 x 62 列 = 1736 格
lead 上界 ⇒ slot <= (lead_max-0xA1+1)*94-1
本脚本给出: 按不同 lead 上界能有多少格 / 现用多少 / 还能放多少 / 与需求的差距。
只读。
"""
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
c = json.load(io.open(CS, encoding='utf-8'))
used_slots = len(c['pair_of'])
print('现役 charset: 对偶 %d 个 (码位占 slot 0..%d)' % (used_slots, used_slots - 1))
print('单字节码 %d 个 (0x80..0xFF 共 128 个码位, 空 %d)'
      % (len(c['codes']), 128 - len(c['codes'])))
print()
print('=== 对偶网格的算术上限 ===')
W, H = 1024, 512
rows_ok = []
for row in range(0, 40):
    y = 2 + 16 * (row + 3 * (row >= 12))
    if y + 16 <= H:
        rows_ok.append(row)
print('  图集 %dx%d ⇒ 能放下的 row: 0..%d (共 %d 行, y 最大 %d)'
      % (W, H, rows_ok[-1], len(rows_ok), 2 + 16 * (rows_ok[-1] + 3 * (rows_ok[-1] >= 12))))
print('  每行 62 列 ⇒ 网格算术上限 = **%d 格**' % (len(rows_ok) * 62))
print()
print('=== 按 lead 上界算可用槽位 ===')
need = 693
free_single = 128 - len(c['codes'])
print('  %-10s %-8s %-10s %-12s %s' % ('lead 上界', 'slot 上限', '网格内可放', '还可放(对偶)', '加上单字节空位'))
best = None
for lead_max in (0xAD, 0xAE, 0xB0, 0xB3, 0xBE, 0xFE):
    slot_max = (lead_max - 0xA1 + 1) * 94 - 1
    grid = len(rows_ok) * 62
    cap = min(slot_max + 1, grid)
    free = cap - used_slots
    if free > 0 and (best is None or free > best[1]):
        best = (lead_max, free)
    print('  0x%02X       %-8d %-10d %-12d %d' % (lead_max, slot_max, cap, free, free + free_single))
print()
print('=== 结论 ===')
if best:
    lead_max, free = best
    print('  最省的扩法: lead 扩到 0x%02X ⇒ 还空 %d 格; 加上单字节空位 %d 个 ⇒ 共 %d 个'
          % (lead_max, free, free_single, free + free_single))
    print('  需求 %d 个 ⇒ %s' % (need, '够' if free + free_single >= need
                                else '**差 %d 个**' % (need - free - free_single)))
print()
print('=== 需要改什么 (历史结论) ===')
print('  · lead 越界曾由 teammate "agent-c-lead" 试过: "尝试方案C: 扩lead到0xB3, 需改所有容器"')
print('    ⇒ 现在有了 font_compact 的**全容器重编码**机制(31 个容器 + ELF + 硬门禁), 这件事可做了')
print('  · 还要: 生成新字形(16px 模板管线已有) + 扩 charset + 重出盘')
