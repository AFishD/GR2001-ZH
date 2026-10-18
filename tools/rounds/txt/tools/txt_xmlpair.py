# -*- coding: utf-8 -*-
"""txt_xmlpair.py —— XML 的 <text> 配对统计（只读），解释为什么逐条口径只覆盖 69/94。"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '..', '..', 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for tag, rel in (('EN', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
                 ('ZH', r"work\builds\GR_ZH113b\GR_ZH113b.iso")):
    iso = T.Iso(os.path.join(ROOT, rel))
    e = iso.img_entry(T.MENU_LBA, 283)
    b = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    iso.close()
    print('== %s  blob=%d' % (tag, len(b)))
    for pat, lab in ((rb'<text>', 'open <text>'), (rb'</text>', 'close </text>'),
                     (rb'<text/>', 'selfclose <text/>'), (rb'<text\s', 'open <text +attr'),
                     (rb'<text[^>]*>', 'open any'), (rb'<item', 'item'),
                     (rb'<picname>', 'picname'), (rb'<br>', 'br')):
        print('   %-22s %d' % (lab, len(re.findall(pat, b))))
    print('   paired <text>..</text>  %d'
          % len(re.findall(rb'<text>.*?</text>', b, re.S)))
    opens = [m.start() for m in re.finditer(rb'<text>', b)]
    closes = [m.start() for m in re.finditer(rb'</text>', b)]
    print('   opens=%d closes=%d' % (len(opens), len(closes)))
    # 逐个 open 往后找第一个 </text>；若中途又出现 <text> 则说明是"未闭合"
    bad = 0
    last = -1
    for o in opens:
        c = b.find(b'</text>', o)
        nxt = b.find(b'<text>', o + 6)
        if c < 0 or (0 <= nxt < c):
            bad += 1
            if bad <= 3:
                print('   未闭合样本 @0x%X: %r' % (o, b[o:o + 90]))
        last = c
    print('   未闭合(下一个 <text> 先于 </text> 或没有 </text>) = %d' % bad)
