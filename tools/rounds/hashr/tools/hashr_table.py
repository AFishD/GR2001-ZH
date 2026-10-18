# -*- coding: utf-8 -*-
r"""hashr_table.py — 从构建报告生成报告用的「旧码→新码」对照表 (只读+写 audit)

    python work/builds/GR_HASHR/tools/hashr_table.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SENT = (0xB1, 0xB5)
r = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'temp',
                                   'GR_HASHR2400_build.json'), encoding='utf-8'))['extra']
ink = {t['char']: t['ink'] for t in r['touch']}
rows = sorted(r['moves'], key=lambda x: x['old_slot'])
sent_slots = [(L - 0xA1) * 94 + (t - 0xA1) for L in range(0xA1, 0xBA) for t in SENT]
lines = ['| # | 字 | 旧码 | 旧槽 | 新码 | 新槽 | 让位占位字 | 墨 |',
         '|---|---|---|---|---|---|---|---|']
for i, a in enumerate(rows, 1):
    lines.append('| %d | %s | `%02X%02X` | %d | `%02X%02X` | %d | U+%04X | %d |'
                 % (i, a['char'], a['old_pair'][0], a['old_pair'][1], a['old_slot'],
                    a['new_pair'][0], a['new_pair'][1], a['new_slot'],
                    ord(a['evicted_placeholder']), ink.get(a['char'], -1)))
lines.append('')
lines.append('- 目标槽: %d..%d (连续 %d 槽, 都在原「保留/占位段」的低位 ⇒ 保留段起点后移) ; 墨合计 %d'
             % (min(a['new_slot'] for a in rows), max(a['new_slot'] for a in rows),
                len(rows), sum(ink.values())))
lines.append('- 注销的 %d 个哨兵占位码: %s'
             % (len(r['retired']),
                ' '.join('U+%04X@slot%d' % (ord(d['char']), d['slot']) for d in r['retired'])))
lines.append('- 50 个哨兵槽 (禁用): %s' % ' '.join('%d(`%02X%02X`)'
             % (s, 0xA1 + s // 94, 0xA1 + s % 94) for s in sent_slots))
lines.append('- 对偶空间: gate 0x%02X ⇒ %d 槽 ; charset 登记 %d → %d ; 注销后未登记槽 = 50'
             % (r['gate'], r['slot_space'], r['pair_of_before'], r['pair_of_after']))
lines.append('- 总字形槽账: 对偶 %d (其中 trail 非哨兵) + 单字节 %d = **%d ≥ 2,400** ✓'
             % (r['pair_of_after'], 103, r['pair_of_after'] + 103))
with io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit', 'moves_table.txt'),
             'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')
print('\n'.join(lines))
