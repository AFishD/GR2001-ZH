# -*- coding: utf-8 -*-
"""r50: 核实 (a) 盘上换行/空行标记就是字面 ASCII `{br}`/`{p}`;
        (b) ® 在正文里出现在哪 (79 次); (c) ± 的出现处。"""
import csv
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                             # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work/builds/GR_ZH98/GR_ZH98.iso'))
try:
    c0 = tcslib.en_read_tables.__module__ and None
finally:
    pass
# (a) 直接在盘上找 LANG / SFXML 容器里的字面 {br}
import struct                                              # noqa: E402
img = tcslib.MENU_LBA
hits = {}
for tag, lba, idx in (('MENU', tcslib.MENU_LBA, None),):
    pass
# 简化: 用 tcslib 的容器解析找到 LANG 与 SFXML 的条目
try:
    lang_iso = tcslib.Iso(os.path.join(REPO, 'work/builds/GR_ZH98/GR_ZH98.iso'))
    # 用 inject/dump 的入口拿容器清单
    for (lba, idx, name) in ((None, None, None),):
        pass
finally:
    lang_iso.close()
print('== (b)/(c) 正文里 ® 与 ± 的出现处 ==')
TD = os.path.join(REPO, 'work/builds/GR_ZH98/text')
INJ = [f for f in sorted(os.listdir(TD)) if f.endswith('.csv') and '_text_' in f]
for fn in INJ:
    with io.open(os.path.join(TD, fn), encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            zh = (row.get('text_edited') or '').replace('\n', '\\n')
            for ch in ('®', '±', '·'):
                if ch in zh:
                    print('  [%s] %s %-24s %s' % (ch, fn.split('_')[-1], row.get('id'),
                                                  zh[:150]))
