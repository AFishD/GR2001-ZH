# -*- coding: utf-8 -*-
"""r51 探针⑮: SFXML 标题属性用**哪一版 charset** 才解得对? (定"陈旧"的年份 + 给出修复映射) 只读。"""
import json
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
spec = tcslib.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
iso.close()

ITEM = re.compile(rb'<(studio|item)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
pairs = []
for m in ITEM.finditer(blob):
    nm = NAME.search(m.group(2))
    if nm:
        pairs.append((m.group(1).decode(), nm.group(1)))

CHARSETS = [
    ('current(r51)', tcslib.CHARSET),
    ('GR_ZH92/93/94 r38-era', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                                           'charset_matching_this_disk.json')),
    ('GR_ZH95 重排前', os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'font_repack',
                                    'charset_before.json')),
    ('GR_ZH95 重排后', os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'r46',
                                    'charset_after_repack.json')),
    ('GR_ZH98 清理前(r49)', os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp',
                                         'charset_before_font_cleanup.json')),
    ('planC 之前', os.path.join(REPO, 'work', '_planc', 'charset_before_planc.json')),
]

# 用"正确答案"当判据: 这些标题里**已知**该是什么
KNOWN = {
    '定向炸、 (M2)': '定向炸药 (M2)',
    'MP5 冲酿枪': 'MP5 冲锋枪',
    'MP5SD 异声冲酿枪': 'MP5SD 消声冲锋枪',
    'M249 灾用机枪': 'M249 班用机枪',
    'M9SD 异声手枪': 'M9SD 消声手枪',
    '测距昨远镜 (AN/GVS-5)': '测距望远镜 (AN/GVS-5)',
}

print('=== 同一段字节在不同 charset 下的解码 ===')
print('%-24s %s' % ('charset', ' | '.join('%-22s' % k for k in KNOWN)))
for label, path in CHARSETS:
    if not os.path.isfile(path):
        print('%-24s (缺文件)' % label)
        continue
    c = tcslib.Charset(path)
    row = []
    for want, _good in KNOWN.items():
        raw = None
        for (tag, val) in pairs:
            t, _ = c.decode(val)
            if t == want:
                raw = val
                break
        row.append(repr(c.decode(raw)[0]) if raw else '-')
    print('%-24s %s' % (label, ' | '.join('%-22s' % x for x in row)))

print()
print('=== 逐条: 现役 charset 解出来的 82 条中文标题 (人工挑错) ===')
c = tcslib.Charset()
n = 0
for (tag, val) in pairs:
    if tag != 'item':
        continue
    t, _ = c.decode(val)
    if any(ord(ch) > 0x7F for ch in t):
        n += 1
        print('  %-30r  bytes=%s' % (t, val.hex(' ')))
print('  共 %d 条含中文的 item 标题' % n)
