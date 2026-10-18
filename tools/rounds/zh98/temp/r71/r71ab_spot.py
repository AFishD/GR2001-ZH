# -*- coding: utf-8 -*-
r"""r71ab_spot.py — 成品抽读: 打印几条改后正文 (人眼验收语气/断裂是否正确)"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text', 'GR_ZH113_B_text_long.csv')
rows = {r['id']: r for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline=''))}
for eid in ('SFXML:T0067', 'SFXML:T0056', 'SFXML:T0066'):
    t = rows[eid]['text_zh']
    print('=' * 96)
    print('### %s   (可见字 %d, 段落 %d, 换行 %d)'
          % (eid, len(t.replace('\n', '')), t.count('\n\n') + 1, t.count('\n')))
    print('-' * 96)
    print(t[:1400])
    print()
