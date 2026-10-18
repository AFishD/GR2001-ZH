# -*- coding: utf-8 -*-
"""r39: 复现并定位 dump_sfxml line 607 的 TypeError (marks 里混进了 int)。只读。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ISO)
cs = T.Charset()
e = iso.img_entry(T.MENU_LBA, T.XML_IDX)
raw = iso.read(e['iso_off'], e['stored'])
subs = T.lzo_subs(raw)
xml = b''.join(s[0] for s in subs)
print('blob=%d 条数=%d' % (len(xml), len(T.parse_sfxml(xml))))
bad = 0
for (k, off, ln, body) in T.parse_sfxml(xml):
    text, _mp = cs.decode(body)
    for ch in text:
        if 0xE000 <= ord(ch) <= 0xE0FF:
            v = T.BTN_FMT % ord(ch)
            if not isinstance(v, str):
                print('  !! id=T%04d  ch=%r ord=%d  BTN_FMT=%r  v=%r (%s)'
                      % (k, ch, ord(ch), T.BTN_FMT, v, type(v)))
                bad += 1
    marks = sorted({T.BTN_FMT % ord(c) for c in text if 0xE000 <= ord(c) <= 0xE0FF})
    if any(not isinstance(x, str) for x in marks):
        print('  T%04d marks 里有非字符串: %r' % (k, marks))
        bad += 1
print('有问题的条目 = %d' % bad)
iso.close()
