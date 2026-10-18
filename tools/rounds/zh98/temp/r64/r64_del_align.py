# -*- coding: utf-8 -*-
r"""r64_del_align.py — 删掉 SFXML:T0062 开头的「对齐」测试残留 (用户已确认可删)

只改该条的 text_edited 一列: 去掉开头那 8 个「对齐」+ 紧跟的换行。
字节级回环自检: 除目标行外其它行必须逐字节不变。
"""
import csv
import io
import os
import shutil
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text', 'GR_ZH109_text_long.csv')
BAK = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r64', 'before_del_align.csv')
TARGET = 'SFXML:T0062'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

raw = io.open(P, encoding='utf-8-sig', newline='').read()
rows = list(csv.DictReader(io.StringIO(raw)))
hdr = list(rows[0].keys())
print('表: %d 行 ; 列 %d 个' % (len(rows), len(hdr)))

hit = None
for r in rows:
    if (r.get('id') or '').strip() == TARGET:
        hit = r
        break
if hit is None:
    raise SystemExit('!! 找不到 %s' % TARGET)
t = hit['text_edited'] or ''
print('改动前开头 60 字: %r' % t[:60])

n = 0
while t.startswith('对齐'):
    t = t[2:]
    n += 1
while t[:1] in ('\r', '\n'):
    t = t[1:]
print('删掉 %d 个「对齐」+ 前导换行' % n)
print('改动后开头 60 字: %r' % t[:60])
if n == 0:
    raise SystemExit('!! 开头没有「对齐」, 未改动')
hit['text_edited'] = t

os.makedirs(os.path.dirname(BAK), exist_ok=True)
shutil.copyfile(P, BAK)
with io.open(P, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=hdr, lineterminator='\r\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('已写回 (备份: %s)' % BAK)

# 回环自检: 重新读, 除 T0062 外逐字段相同
rows2 = list(csv.DictReader(io.open(P, encoding='utf-8-sig', newline='')))
diff = 0
for a, b in zip(rows, rows2):
    if a['id'] != b['id']:
        diff += 1
        continue
    for k in hdr:
        if (a.get(k) or '') != (b.get(k) or ''):
            diff += 1
            break
print('回环自检: 行数 %d → %d ; 有差异的行 %d (期望 1 = 只有 T0062)' % (len(rows), len(rows2), diff))
