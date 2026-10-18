# -*- coding: utf-8 -*-
r"""r60_recon_sf3.py — 打出"特别收录"完整结构树, 定位"开发访谈"及其第一篇

只读。解码 = ASCII 直通 + 中文走现役码表(对偶/单字节)。
输出: studio/group/item 三级树 + 每篇正文长度 + "开发访谈"的定位结论。
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
        x = b[i]
        if x < 0x80:                       # ★ ASCII 直通 (上一版漏了这个)
            out.append(chr(x)); i += 1
        elif ('S', x) in M:
            out.append(M[('S', x)]); i += 1
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
print('展开 %d B → 解出 %d 字符 (ASCII 直通 + 中文码表)' % (len(blob), len(xml)))
print()

# 逐行扫, 维护 studio/group 栈
stack = []
items = []
for m in re.finditer(r'<(\w+)([^>]*)>|</(\w+)>', xml):
    open_tag, attrs, close_tag = m.group(1), m.group(2), m.group(3)
    if close_tag:
        if close_tag in ('studio', 'group') and stack:
            stack.pop()
        continue
    nm = re.search(r'name="([^"]*)"', attrs)
    nmv = nm.group(1) if nm else ''
    if open_tag == 'studio':
        stack = [('studio', nmv)]
        print('[studio] %s' % nmv)
    elif open_tag == 'group':
        if len(stack) > 1:
            stack = stack[:1]
        stack.append(('group', nmv))
        print('  [group] %s' % nmv)
    elif open_tag == 'item':
        items.append((list(stack), nmv, m.start()))
        print('    [item] %-30s @0x%X' % (nmv, m.start()))

print()
texts = [(m.start(), m.group(1), m.group(2)) for m in
         re.finditer(r'<text([^>]*)>(.*?)</text>', xml, re.S)]
print('=== <text> %d 个, 非空 %d 个 ===' % (len(texts), sum(1 for _p, _a, t in texts if t.strip())))
for i, (pos, a, t) in enumerate(texts):
    if not t.strip():
        continue
    tid = re.search(r'id="([^"]*)"', a)
    print('  [%2d] @0x%X id=%-10s %5d 字  %s' % (i, pos, (tid.group(1) if tid else '?'), len(t), t[:50].replace('\n', ' ')))

print()
print('=== "开发访谈" 定位 ===')
for m in re.finditer(r'开发访谈', xml):
    p = m.start()
    before = xml[max(0, p - 200):p].replace('\n', ' ')
    after = xml[p:p + 120].replace('\n', ' ')
    print('  @0x%X' % p)
    print('    前文: ...%s' % before[-160:])
    print('    后文: %s...' % after)
