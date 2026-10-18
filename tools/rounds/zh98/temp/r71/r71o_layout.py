# -*- coding: utf-8 -*-
r"""r71o_layout.py — 准备 GR_ZH113b 的注入输入表 (3 张)

· text_long.csv        = 本轮产物 (丰富版底本 + 16 条低精准度缩减 + 9 条高精准度最小伤害替换)
· text_long_nowrap.csv = 现役 GR_ZH113 原样 (未改)
· text_short.csv       = 现役 GR_ZH113 原样 (未改)
另外在 temp/r71/ 留一份 text_backup_before_r71 内容(丰富版底本, 未做 r71 改写),
等构筑完成后由 r71p 复制进 work/builds/GR_ZH113b/text_backup_before_r71/。
"""
import csv
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
T113 = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
INJ = os.path.join(HERE, 'inject')
BAK = os.path.join(HERE, 'text_backup_before_r71')
BKP_SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix',
                       'GR_ZH109_text_long.csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WRAPS = re.compile(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}')

os.makedirs(INJ, exist_ok=True)
os.makedirs(BAK, exist_ok=True)

# ---- 1) 恢复丰富版底本 (wrapfix) ----
rows = list(csv.DictReader(io.open(BKP_SRC, encoding='utf-8-sig', newline='')))
n_fix = 0
for r in rows:
    t = r['text_edited'] or ''
    if WRAPS.search(t):
        n_fix += len(WRAPS.findall(t))
        r['text_edited'] = WRAPS.sub('\n\n', t)
print('wrapfix: 修了 %d 处 {WRAP}{WRAP}' % n_fix)


def write_csv(path, rows, ver):
    with io.open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\r\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('  -> %s (%d 行)' % (os.path.relpath(path, REPO), len(rows)))


# ---- 2) 备份: 丰富版底本 (未做 r71 改写) ----
write_csv(os.path.join(BAK, 'GR_ZH113b_text_long.csv'), [dict(r) for r in rows], 'bak')
for k in ('long_nowrap', 'short'):
    src = os.path.join(T113, 'GR_ZH113_text_%s.csv' % k)
    dst = os.path.join(BAK, 'GR_ZH113b_text_%s.csv' % k)
    with io.open(src, 'rb') as fi, io.open(dst, 'wb') as fo:
        fo.write(fi.read())
    print('  -> %s (现役原样)' % os.path.relpath(dst, REPO))

# ---- 3) 注入表: 本轮产物 ----
write_csv(os.path.join(INJ, 'GR_ZH113b_text_long.csv'),
          list(csv.DictReader(io.open(os.path.join(HERE, 'r71_reduced_long.csv'),
                                     encoding='utf-8-sig', newline=''))), 'new')
for k in ('long_nowrap', 'short'):
    src = os.path.join(T113, 'GR_ZH113_text_%s.csv' % k)
    dst = os.path.join(INJ, 'GR_ZH113b_text_%s.csv' % k)
    with io.open(src, 'rb') as fi, io.open(dst, 'wb') as fo:
        fo.write(fi.read())
    print('  -> %s (现役原样)' % os.path.relpath(dst, REPO))
print('注入目录:', os.path.relpath(INJ, REPO))
