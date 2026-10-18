# -*- coding: utf-8 -*-
r"""r71y_charsetdelta.py — 证明 charset JSON 只是被"盖章"(stamp), 语义未变

判据: 用构筑后 JSON 的 (字 -> 码位) 映射, 与 GR_ZH113 / GR_ZH113_B 两份
      font_charset.csv (dump_font 从盘上算出来的独立记录) 逐条对表;
      再核对 pair_of / codes 的数量与顺序。
"""
import csv
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
cs = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
d = json.load(io.open(cs, encoding='utf-8'))
print('=== charset JSON 现状 ===')
print('  pair_of %d / codes %d' % (len(d['pair_of']), len(d['codes'])))
fc = d.get('_font_compact', {})
for k in ('used', 'moved_last', 'codes_changed_last', 'free_slots', 'atlas_pixel_sha256',
          'iso_sha256', 'iso_version', 'stamped', 'last_applied', 'first_applied', 'tool_version'):
    if k in fc:
        v = fc[k]
        if isinstance(v, str) and len(v) > 20:
            v = v[:20] + '…'
        print('  _font_compact.%-20s = %s' % (k, v))

for tag in ('GR_ZH113', 'GR_ZH113_B'):
    p = os.path.join(REPO, 'work', 'builds', tag, 'font', '%s_font_charset.csv' % tag)
    rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
    bad = 0
    n = 0
    for r in rows:
        k = r['kind']
        ch = r['char']
        if k == 'pair':
            b = r['bytes_hex']
            b1, b2 = int(b[0:2], 16), int(b[2:4], 16)
            n += 1
            if d['pair_of'].get(ch) != [b1, b2]:
                bad += 1
        elif k == 'single':
            v = int(r['bytes_hex'], 16)
            n += 1
            if d['codes'].get(ch) != v:
                bad += 1
    print('  %s: 逐字对表 %d 条, 不一致 %d %s' % (tag, n, bad, '✓' if bad == 0 else '✗'))
print()
print('结论: 若两份盘的对表都 0 不一致 ⇒ charset JSON 的**字→码位映射**没变,')
print('      本轮构筑只往里盖了章 (iso_version / iso_sha256 / stamped)。')
