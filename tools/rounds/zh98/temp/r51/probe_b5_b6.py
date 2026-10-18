# -*- coding: utf-8 -*-
"""r51 探针⑰ (任务B5/B6): GR_ZH94 vs GR_ZH95 的 T0063 标题字段字节 + 各自 charset 下的解码。

B5: GR_ZH95 当初是"开重排交付"的 ⇒ 它的标题是不是也错?
B6: 现役盘 GR_ZH98 不受影响 —— 要正面证据。
只读。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

ITEM = re.compile(rb'<(studio|item)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')


def titles(iso_path):
    iso = tcslib.Iso(iso_path)
    spec = tcslib.RES['SFXML']['copies'][0]
    e = iso.img_entry(spec[1], spec[2])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    iso.close()
    out = []
    for m in ITEM.finditer(blob):
        nm = NAME.search(m.group(2))
        out.append((m.group(1).decode(), nm.group(1) if nm else b''))
    return blob, out


CS = {
    'GR_ZH92/93/94 配套 (旧)': os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                                            'charset_matching_this_disk.json'),
    'GR_ZH95 重排后': os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'r46',
                                   'charset_after_repack.json'),
    'GR_ZH95 重排前': os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'font_repack',
                                   'charset_before.json'),
    '现役 (r51)': tcslib.CHARSET,
}
BUILDS = ['GR_ZH94', 'GR_ZH95', 'GR_ZH97', 'GR_ZH98']
data = {}
for b in BUILDS:
    p = os.path.join(REPO, 'work', 'builds', b, b + '.iso')
    if os.path.isfile(p):
        data[b] = titles(p)

print('=== 标题属性字节: 各盘之间是否相同 (104 条) ===')
ref = data['GR_ZH94'][1]
for b, (blob, at) in data.items():
    same = sum(1 for i in range(len(ref)) if at[i][1] == ref[i][1])
    print('  %-10s 与 GR_ZH94 相同 %d/%d' % (b, same, len(ref)))

print()
print('=== 用各版 charset 解码同一个"何为幽灵"标题属性 ===')
idx = None
for i, (tag, v) in enumerate(ref):
    if tag == 'item':
        t, _ = tcslib.Charset().decode(v)
        if t.startswith('何为'):
            idx = i
            break
print('  条目下标 = %d' % idx)
for label, path in CS.items():
    if not os.path.isfile(path):
        print('  %-24s (缺文件)' % label)
        continue
    c = tcslib.Charset(path)
    row = []
    for b in BUILDS:
        if b not in data:
            continue
        v = data[b][1][idx][1]
        row.append('%s=%r' % (b, c.decode(v)[0]))
    print('  %-24s %s' % (label, '  '.join(row)))

print()
print('=== 每个盘的标题在该盘自己的 charset 下解出来是什么 (前 12 条中文标题) ===')
OWN = {
    'GR_ZH94': CS['GR_ZH92/93/94 配套 (旧)'],
    'GR_ZH95': CS['GR_ZH95 重排后'],
    'GR_ZH97': os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'temp', 'r49', 'dryrun', 'temp',
                            'charset_for_residue.json'),
    'GR_ZH98': tcslib.CHARSET,
}
for b in BUILDS:
    if b not in data:
        continue
    p = OWN.get(b)
    if not p or not os.path.isfile(p):
        print('  %-10s (无配套 charset)' % b)
        continue
    c = tcslib.Charset(p)
    got = []
    for (tag, v) in data[b][1]:
        if tag != 'item':
            continue
        t, _ = c.decode(v)
        if any(ord(x) > 0x7F for x in t):
            got.append(t)
    print('  %-10s %s' % (b, ' | '.join(got[:12])))
