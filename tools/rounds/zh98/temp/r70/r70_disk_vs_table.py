# -*- coding: utf-8 -*-
r"""r70_disk_vs_table.py — 直接读盘上 SFXML 的实际字符串, 与文本表比对

回答: GR_ZH114 的盘上正文, 到底与 GR_ZH111/GR_ZH114 的表里哪一份一致?
"""
import csv
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

c = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                   'charset_compiled_zh16.json'), encoding='utf-8'))
pair = {(a, b): ch for ch, (a, b) in c['pair_of'].items()}
sing = {v: ch for ch, v in c['codes'].items()}


def dec(b):
    o, i = [], 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            o.append(chr(x)); i += 1
        elif x in sing:
            o.append(sing[x]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in pair:
            o.append(pair[(b[i], b[i + 1])]); i += 2
        else:
            o.append('?'); i += 1
    return ''.join(o)


def xml_text(ver):
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', ver, ver + '.iso'))
    spec = tcslib.RES['SFXML']['copies'][0]
    e = iso.img_entry(spec[1], spec[2])
    st = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(st))
    return dec(blob)


print('=== 盘上 SFXML 里 T0010 (M18 地雷) 的实际字符串 ===')
for ver in ('GR_ZH109', 'GR_ZH111', 'GR_ZH113', 'GR_ZH114'):
    try:
        x = xml_text(ver)
    except Exception as ex:
        print('  %-10s ✗ %s' % (ver, ex)); continue
    m = re.search(r'<item name="([^"]*)">\s*<text[^>]*>((?:(?!</text>).)*)', x, re.S)
    # 直接找 M18 那段
    i = x.find('M18 定向反步兵地雷')
    if i < 0:
        i = x.find('M18')
    seg = re.sub(r'\s+', '／', x[i:i + 210]) if i >= 0 else '(未找到 M18)'
    print('  %-10s %s' % (ver, seg))

print()
print('=== 与各表 text_edited/text_zh 的对应 ===')
for ver in ('GR_ZH111', 'GR_ZH114'):
    p = os.path.join(REPO, 'work', 'builds', ver, 'text', ver + '_text_long.csv')
    if not os.path.isfile(p):
        print('  %-10s (无 long 表)' % ver); continue
    rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
    for r in rows:
        if r.get('id') == 'SFXML:T0010':
            te = (r.get('text_edited') or '').replace('\n', '／')
            tz = (r.get('text_zh') or '').replace('\n', '／')
            print('  %-10s text_edited[:90]: %s' % (ver, te[:90]))
            print('  %-10s text_zh    [:90]: %s' % ('', tz[:90]))
            break
