# -*- coding: utf-8 -*-
r"""m19_enband.py — ASCII 带在哪几行? 打印 ASCII 记录的 v0 分布 + 各 face 的 CJK 记录 v0 分布。
"""
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
iso = tcslib.Iso(BASE)
ft_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'FONT.RES':
        ft_e = e
ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
iso.close()
_he, faces = tcslib.parse_ft_faces(ft_blob)
for (nm, fld, recs) in faces:
    print('=== face %s nrec=%d fld=%s' % (nm, len(recs), fld))
    c_ascii, c_single = Counter(), Counter()
    for code, rec in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        c = code + 0x20
        if c < 0x80:
            c_ascii[(v0, v1)] += 1
        elif c >= 0xAF:
            c_single[(v0, v1)] += 1
    print('   ASCII 码记录 (v0,v1) 分布: %s' % dict(sorted(c_ascii.items())))
    print('   0xAF+ 单字节记录 (v0,v1) 分布: %s' % dict(sorted(c_single.items())))

# FIXED 盘: 修复补丁给 35 个新单字节码写的记录
import json
js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
meta = js.get('_font_ext_zh93_fix', {})
codes = [c for c, _ch in meta.get('single_codes', [])]
print()
print('修复补丁 35 个新单字节码的 default 记录:')
recs = faces[1][2]
for c in codes:
    _b0, _b1, u0, v0, u1, v1 = recs[c - 0x20]
    print('   0x%02X rec=(%4d,%3d,%4d,%3d)  引擎格=(%4d,%3d)'
          % (c, u0, v0, u1, v1, (u0 + 576) % 1024, v0 + 1))
