# -*- coding: utf-8 -*-
"""r51 探针⑱: 补全统计 —— group name 属性里有多少陈旧; 28 字在各文本行的用量。只读。"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

OLD = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                                  'charset_matching_this_disk.json'))
NEW = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso'))
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
iso.close()

ITEM = re.compile(rb'<(studio|item|group)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
stat = {}
stale = []
for m in ITEM.finditer(blob):
    nm = NAME.search(m.group(2))
    if not nm:
        continue
    tag = m.group(1).decode()
    v = nm.group(1)
    o, n = OLD.decode(v)[0], NEW.decode(v)[0]
    d = stat.setdefault(tag, dict(total=0, cjk=0, stale=0))
    d['total'] += 1
    if any(ord(c) > 0x7F for c in n):
        d['cjk'] += 1
    if o != n:
        d['stale'] += 1
        stale.append((tag, n, o))
print('=== name 属性统计 (SFXML) ===')
for k in sorted(stat):
    print('  %-8s 共 %3d, 含中文 %3d, **陈旧 %3d**' % (k, stat[k]['total'], stat[k]['cjk'],
                                                      stat[k]['stale']))
print('  合计: %d 个属性, 含中文 %d, 陈旧 %d'
      % (sum(v['total'] for v in stat.values()), sum(v['cjk'] for v in stat.values()),
         sum(v['stale'] for v in stat.values())))
print()
print('=== 陈旧清单 (按 tag) ===')
for tag, n, o in stale:
    print('  %-8s %-24r → %r' % (tag, n[:24], o[:24]))

print()
print('=== 28 个单字节汉字在各文本行里的用量 (3 张可注入表) ===')
TARGETS = set(NEW.codes[c] for c in sorted(NEW.codes) if 0x80 <= c <= 0x9C)
rows = {}
for fn in ('GR_ZH98_text_long.csv', 'GR_ZH98_text_long_nowrap.csv', 'GR_ZH98_text_short.csv'):
    p = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text', fn)
    for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')):
        t = r.get('text_zh') or ''
        hit = sorted(TARGETS & set(t))
        if hit:
            rows[r['id']] = (r['resource'], ''.join(hit))
for k in sorted(rows):
    print('  %-14s %-8s %s' % (k, rows[k][0], rows[k][1]))
print('  共 %d 行, %d 个字次' % (len(rows), sum(len(v[1]) for v in rows.values())))
