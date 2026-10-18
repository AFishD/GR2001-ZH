# -*- coding: utf-8 -*-
"""r51 探针⑭: SFXML 的 name 属性在 EN 原盘 / 各中文盘上是什么? (判断"标题是否陈旧") 只读。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

cs = tcslib.Charset()
ITEM = re.compile(rb'<(studio|item)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')


def attrs_of(iso_path):
    iso = tcslib.Iso(iso_path)
    spec = tcslib.RES['SFXML']['copies'][0]
    e = iso.img_entry(spec[1], spec[2])
    raw = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))
    iso.close()
    out = []
    for m in ITEM.finditer(blob):
        nm = NAME.search(m.group(2))
        out.append((m.group(1).decode(), nm.group(1) if nm else b''))
    return blob, out


BUILDS = ['GR_EN_ORIG', 'GR_ZH93', 'GR_ZH95', 'GR_ZH97', 'GR_ZH98', 'GR_ZH100']
data = {}
for b in BUILDS:
    p = os.path.join(REPO, 'work', 'builds', b, b + '.iso')
    if not os.path.isfile(p):
        continue
    blob, at = attrs_of(p)
    data[b] = (blob, at)
    print('%-12s blob=%d 属性=%d sha256(blob)=%s' % (b, len(blob), len(at),
                                                     tcslib.sha256_file(p)[:12]))

base = data.get('GR_ZH98')
print()
print('=== 属性字节在各盘之间是否相同 (以 GR_ZH98 为基准) ===')
for b, (blob, at) in data.items():
    if b == 'GR_ZH98':
        continue
    same = sum(1 for i in range(min(len(at), len(base[1]))) if at[i][1] == base[1][i][1])
    diff = [i for i in range(min(len(at), len(base[1]))) if at[i][1] != base[1][i][1]]
    print('  %-12s 相同 %d/%d; 不同 %d 个 (前 5: %s)'
          % (b, same, len(base[1]), len(diff), diff[:5]))

print()
print('=== GR_EN_ORIG vs GR_ZH98 逐条 (前 40 条) ===')
if 'GR_EN_ORIG' in data:
    for i, ((t1, v1), (t2, v2)) in enumerate(zip(data['GR_EN_ORIG'][1], base[1])):
        e1, _ = cs.decode(v1)
        e2, _ = cs.decode(v2)
        if i < 40 or v1 != v2:
            if i < 40:
                print('  #%-3d EN %-34r ZH98 %r' % (i, e1[:34], e2[:34]))
print()
print('=== 与"英文原盘不同"的属性条数 ===')
if 'GR_EN_ORIG' in data:
    n = sum(1 for (t1, v1), (t2, v2) in zip(data['GR_EN_ORIG'][1], base[1]) if v1 != v2)
    print('  %d / %d 条属性被改过 (⇒ 说明**有补丁写过它们**, 不是原样英文)' % (n, len(base[1])))
