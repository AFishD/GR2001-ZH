# -*- coding: utf-8 -*-
r"""r60_target_probe.py — 只读: 打印 SFXML 目标 <text> 的**字节**区间 / 原文尾部标记 / 容器槽位。
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
import inject_text_csv as inj  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

cs = tcslib.Charset(CS)
iso = tcslib.Iso(ISO)
spec = tcslib.RES['SFXML']['copies'][0]
c = inj.Container(iso, 'SFXML', spec, cs)
print('container tag=%s img=%s idx=%d  slot=%d  blob=%d  subs=%d  used_end=%d tail_free=%d'
      % (c.tag, c.img, c.idx, c.slot, len(c.blob), len(c.subs), c.used_end,
         len(c.blob) - c.used_end))
print('sizes=%s' % (c.sizes,))
print('entry=%s' % ({k: v for k, v in c.entry.items() if k != 'name'},))
print()

for e in c.ents:
    k, off, ln, data = e['k'], e['off'], e['ln'], e['data']
    txt, _ = cs.decode(data)
    if '开发手记' in txt or 'dev' in txt.lower():
        print('--- T%04d  off=0x%X  ln=%d  end=0x%X' % (k, off, ln, off + ln))
        print('    head64 = %s' % data[:64].hex(' '))
        print('    tail64 = %s' % data[-64:].hex(' '))
        print('    text   = %r' % txt[:60])
        print('    tail   = %r' % txt[-60:])
        print('    markers at tail: br=%d p=%d' % (txt.count('{br}'), txt.count('{p}')))
        print('    last 12 chars = %r' % txt[-12:])

# 目标: Interview 第一个 item 的 <text>
m = re.search(rb'<studio name="Interview"[^>]*>', c.blob)
print()
print('studio Interview tag @0x%X' % m.start())
# 在该 studio 内找第一个 <text ...>
m2 = re.compile(rb'<text\b[^>]*>').search(c.blob, m.start())
m3 = re.compile(rb'</text>').search(c.blob, m2.end())
print('first <text> open @0x%X  close @0x%X  body=[0x%X,0x%X) len=%d'
      % (m2.start(), m3.start(), m2.end(), m3.start(), m3.start() - m2.end()))
print('open tag = %r' % c.blob[m2.start():m2.end()])
body = c.blob[m2.end():m3.start()]
t, mp = cs.decode(body)
print('body decodes to %d chars; head=%r tail=%r' % (len(t), t[:40], t[-40:]))
print('roundtrip strict ok? %s' % (cs.encode_strict(t) == body))
print('body == T66 data? %s' % (body == [e['data'] for e in c.ents if e['k'] == 66][0]))
print('item name before text: %r' % c.blob[m.start():m2.start()][-160:])
iso.close()
