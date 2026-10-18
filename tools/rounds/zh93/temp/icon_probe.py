# -*- coding: utf-8 -*-
r"""icon_probe.py — 查图标码到底有几个: 逐 face 看有墨记录 + 文本里实际用到的 PUA"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
FT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'font', 'GR_ZH93_font_ft.csv')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rows = list(csv.DictReader(io.open(FT, encoding='utf-8-sig'))) if os.path.isfile(FT) else []
print('FT 记录表:', os.path.relpath(FT, REPO), '→', len(rows), '行')
faces = {}
for r in rows:
    faces.setdefault((r['face'], r['face_name']), []).append(r)
for (fi, name), rs in sorted(faces.items()):
    ink = [r for r in rs if r['has_ink'] in ('1', 'True', 'true')]
    print('  face %s (%s): 记录 %d, 有墨 %d' % (fi, name, len(rs), len(ink)))
    if ink:
        codes = sorted(int(r['code'], 16) if r['code'].lower().startswith('0x') else int(r['code'], 16)
                        for r in ink)
        print('     有墨码位: %s' % ' '.join('%02X' % c for c in codes[:40]))
        print('     墨点数 top: %s' % ', '.join('%s=%s' % (r['code'], r['ink_px']) for r in
                                               sorted(ink, key=lambda x: -int(x['ink_px']))[:10]))

# 文本里实际用到的 PUA
print()
print('=== 文本里实际用到的图标 (PUA U+E080..U+E0FF) ===')
used = {}
for n in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text'))):
    if not n.endswith('.csv'):
        continue
    for r in csv.DictReader(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text', n),
                                    encoding='utf-8-sig')):
        for col in ('text_zh', 'text_edited'):
            t = r[col]
            for i in range(len(t) - 8):
                if t.startswith('{{BTN:', i):
                    code = t[i + 6:i + 10]
                    used.setdefault(code, []).append('%s/%s' % (n.replace('GR_ZH93_text_', '').replace('.csv', ''), r['id']))
print('  用到的图标码: %d 个' % len(used))
for c, ids in sorted(used.items()):
    print('    %s  ×%-3d 例: %s' % (c, len(ids), ', '.join(ids[:3])))
