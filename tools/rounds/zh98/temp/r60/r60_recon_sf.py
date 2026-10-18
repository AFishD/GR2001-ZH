# -*- coding: utf-8 -*-
r"""r60_recon_sf.py — 侦察"特别收录"的条目结构, 找"开发者访谈"及其第一篇

只读。用现役码表把 EN_SPECIAL_FEATURE.XML 解成文本, 列出:
  · 所有 <item name=...> 条目 (按文档顺序 = 菜单顺序?)
  · 所有 <text> 元素 (id + 长度 + 前 60 字)
  · 标出"开发者访谈"相关的条目
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

c = json.load(io.open(CS, encoding='utf-8'))
M = {}
for ch, (b1, b2) in c['pair_of'].items():
    M[(b1, b2)] = ch
for ch, bb in c['codes'].items():
    if isinstance(bb, list):
        M[(bb[0], bb[1])] = ch
    else:
        M[('S', bb)] = ch


def dec(b):
    out = []
    i = 0
    while i < len(b):
        if ('S', b[i]) in M:
            out.append(M[('S', b[i])]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in M:
            out.append(M[(b[i], b[i + 1])]); i += 2
        else:
            out.append('\u00b7'); i += 1
    return ''.join(out)


iso = tcslib.Iso(ISO)
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
raw = iso.read(e['iso_off'], e['stored'])
blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))
xml = dec(blob)
print('EN_SPECIAL_FEATURE.XML: 展开 %d B, 解出文本 %d 字符' % (len(blob), len(xml)))
print('容器: IMG#%d entry=%d iso_off=0x%X' % (spec[1], spec[2], e['iso_off']))
print()

items = re.findall(r'<item([^>]*)>', xml)
print('=== <item> 共 %d 个 (文档顺序) ===' % len(items))
for i, a in enumerate(items):
    nm = re.search(r'name="([^"]*)"', a)
    other = re.sub(r'name="[^"]*"', '', a).strip()
    print('  [%3d] name=%-28s %s' % (i, (nm.group(1) if nm else '?')[:28], other[:60]))
print()

texts = re.findall(r'<text([^>]*)>(.*?)</text>', xml, re.S)
print('=== <text> 共 %d 个 ===' % len(texts))
for i, (a, t) in enumerate(texts):
    tid = re.search(r'id="([^"]*)"', a)
    if not t.strip():
        continue
    print('  [%3d] id=%-12s %4d 字  %s' % (i, (tid.group(1) if tid else '?'), len(t), t[:60].replace('\n', ' ')))
print()

print('=== 含"开发者"或"访谈"的位置 ===')
for m in re.finditer(r'.{60}(开发者|访谈).{60}', xml):
    print('  ...%s...' % m.group(0).replace('\n', ' '))
