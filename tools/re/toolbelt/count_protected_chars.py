# -*- coding: utf-8 -*-
r"""count_protected_chars.py — 数 0xB1..0xB4（△/键/练/用）在译文里的出现次数

决策依据: gate 0xB1→0xB5 会把 0xB1..0xB4 从"单字节码"变成"对偶 lead" ⇒
          这 4 个字必须迁移（改成对偶码或换字）⇒ 需要知道各出现几次。
"""
import glob
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CHARS = {'0xB1': '△', '0xB2': '键', '0xB3': '练', '0xB4': '用'}
DIRS = [
    'work/builds/GR_ZH109/text_backup_before_reduce',   # 用户丰富版
    'work/builds/GR_ZH113b/text',                        # 盘上现值
]

for dd in DIRS:
    p = os.path.join(REPO, dd)
    if not os.path.exists(p):
        print('(缺 %s)' % dd)
        continue
    files = sorted(glob.glob(os.path.join(p, '*.csv')))
    print('=' * 70)
    print('%s  (%d 个 csv)' % (dd, len(files)))
    counts = {k: 0 for k in CHARS}
    entry_hits = {k: [] for k in CHARS}
    for f in files:
        txt = open(f, encoding='utf-8', errors='replace').read()
        for code, ch in CHARS.items():
            c = txt.count(ch)
            if c:
                counts[code] += c
                entry_hits[code].append('%s×%d' % (os.path.basename(f), c))
    for code, ch in CHARS.items():
        print('  %s 「%s」 出现 **%d** 次' % (code, ch, counts[code]))
        if entry_hits[code]:
            print('      分布: %s' % ', '.join(entry_hits[code][:6]))
    print()
    print('  ⇒ 4 个字合计 %d 次' % sum(counts.values()))
    print('  ⇒ 迁移成本 = 把这 %d 处改成对偶码/换字（若全用对偶码，还需 4 个新槽位）' % sum(counts.values()))
    print()
