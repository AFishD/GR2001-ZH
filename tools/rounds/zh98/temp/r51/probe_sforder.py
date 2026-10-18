# -*- coding: utf-8 -*-
"""r51 探针⑬: SFXML 的 studio/item 顺序 —— 用来算实机导航"下移几次"到含 28 字的条目。只读。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

cs = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso'))
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))

TARGETS = set('《》享伞促凝双吸壳套尖履巨拆捕旋池热燃牛牲牺猪玻璃磁磅稳')
item_i = 0
studio_i = -1
for m in re.finditer(rb'<(studio|item)\b([^>]*)>', blob):
    tag = m.group(1).decode()
    am = re.search(rb'name\s*=\s*"([^"]*)"', m.group(2))
    val = am.group(1) if am else b''
    txt, _ = cs.decode(val)
    if tag == 'studio':
        studio_i += 1
        print()
        print('--- studio#%d  name=%r ---' % (studio_i, txt))
        item_i = 0
        continue
    hit = sorted(set(txt) & TARGETS)
    print('  item#%-3d %-28r %s' % (item_i, txt[:28], ('★含目标字: ' + ''.join(hit)) if hit else ''))
    item_i += 1
iso.close()
