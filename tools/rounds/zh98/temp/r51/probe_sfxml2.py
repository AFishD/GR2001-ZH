# -*- coding: utf-8 -*-
"""r51 探针⑪b: EN_SPECIAL_FEATURE.XML 原始结构与 T0063 附近 —— 标题存在哪个字段? 只读。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
iso = tcslib.Iso(ISO)
lba, ent, _tag = tcslib.RES['SFXML']['copies'][0][1], tcslib.RES['SFXML']['copies'][0][2], None
e = iso.img_entry(lba, ent)
print('SFXML 条目: name=%s iso_off=%d stored=%d' % (e['name'], e['iso_off'], e['stored']))
raw = iso.read(e['iso_off'], e['stored'])
blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))
print('展开 %d B; 头 32B = %s' % (len(blob), blob[:32].hex(' ')))

body = blob[28:] if len(blob) > 28 else blob
txt = body.decode('latin-1')
print()
print('=== 第一个 <text> 元素之前 1200 字符 (看元素属性/标题字段) ===')
i = txt.find('<text')
print(repr(txt[max(0, i - 900):i + 200]))
print()
print('=== T0063 的 offset=53472 附近 ===')
seg = body[53472 - 260:53472 + 500]
print(repr(seg.decode('latin-1')))
print()
print('=== 结构骨架 (把所有 tag 名与属性名列出来) ===')
tags = re.findall(rb'<([A-Za-z_][\w:.-]*)', body)
from collections import Counter
print(Counter(t.decode('latin-1') for t in tags).most_common(30))
print()
print('=== 属性名 ===')
attrs = re.findall(rb'([A-Za-z_][\w:.-]*)\s*=\s*"', body)
print(Counter(a.decode('latin-1') for a in attrs).most_common(30))
