# -*- coding: utf-8 -*-
r"""r71_del_align.py — 再删一次 SFXML:T0062 开头的「对齐」测试残留

原因: 任务 e6948df8 的底本用了 text_backup_before_wrapfix（早于 r64 的删除）
      ⇒ 那 16 个字随底本复活。用户已确认"可以随意删除"。
目标: work/builds/GR_ZH113b/text/GR_ZH113b_text_long.csv（当前产物表）
      以及 work/builds/GR_ZH113_B/text/ 里的同名表（若存在）
只改该条 text_edited 一列; 改完必须重跑预检。
"""
import csv
import io
import os
import shutil
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TARGET = 'SFXML:T0062'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cands = []
for ver in ('GR_ZH113b', 'GR_ZH113_B'):
    d = os.path.join(REPO, 'work', 'builds', ver, 'text')
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith('_text_long.csv'):
                cands.append(os.path.join(d, fn))

if not cands:
    raise SystemExit('!! 找不到产物表')

BAK = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71', 'before_del_align')
os.makedirs(BAK, exist_ok=True)

for p in cands:
    raw = io.open(p, encoding='utf-8-sig', newline='').read()
    rows = list(csv.DictReader(io.StringIO(raw)))
    hdr = list(rows[0].keys())
    hit = None
    for r in rows:
        if (r.get('id') or '').strip() == TARGET:
            hit = r
            break
    if hit is None:
        print('  %-46s 找不到 %s' % (os.path.basename(p), TARGET)); continue
    t = hit['text_edited'] or ''
    if not t.startswith('对齐'):
        print('  %-46s 开头不是「对齐」(已是干净的): %r' % (os.path.basename(p), t[:24])); continue
    n = 0
    while t.startswith('对齐'):
        t = t[2:]; n += 1
    while t[:1] in ('\r', '\n'):
        t = t[1:]
    hit['text_edited'] = t
    shutil.copyfile(p, os.path.join(BAK, os.path.basename(p)))
    with io.open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=hdr, lineterminator='\r\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('  %-46s 删掉 %d 个「对齐」; 新开头: %r' % (os.path.basename(p), n, t[:30]))

print()
print('备份:', BAK)
