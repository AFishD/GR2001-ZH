# -*- coding: utf-8 -*-
r"""r60_recon_sf2.py — 看清 EN_SPECIAL_FEATURE.XML 的原始结构 (标签/分隔/条目)

只读。直接看原始字节: 标签用什么编码、条目怎么分、每篇正文从哪到哪。
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
iso = tcslib.Iso(ISO)
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
raw = iso.read(e['iso_off'], e['stored'])
blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))

print('展开 %d B ; 头部 512 B 的 hex+可见形式:' % len(blob))
head = blob[:512]
for i in range(0, 256, 32):
    chunk = head[i:i + 32]
    hexs = ' '.join('%02X' % b for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('  %04X  %-95s  %s' % (i, hexs, asc))
print()
# 找 ASCII 标签
for pat in (b'<item', b'<text', b'<?xml', b'<root', b'<SF', b'name='):
    n = blob.count(pat)
    first = blob.find(pat)
    print('  %-8s 出现 %d 次 ; 首次 0x%X' % (pat.decode(), n, first if first >= 0 else -1))
print()
# 找 UTF-16LE 形式的标签
u16 = b''.join(bytes([b, 0]) for b in b'<item')
print('  UTF-16LE "<item" 出现 %d 次' % blob.count(u16))
print()
# 把 blob 按 2 字节对齐当 UTF-16LE 试解
try:
    t = blob[:2000].decode('utf-16-le', 'replace')
    print('按 UTF-16LE 解前 2000 B:')
    print('  ' + repr(t[:300]))
except Exception as ex:
    print('  utf-16 失败:', ex)
print()
# 直接用 latin-1 看所有 >=0x80 的字节分布
from collections import Counter
cnt = Counter(blob)
print('字节分布 top 20: %s' % cnt.most_common(20))
