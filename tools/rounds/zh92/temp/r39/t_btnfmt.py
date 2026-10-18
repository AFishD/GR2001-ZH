# -*- coding: utf-8 -*-
"""r39: 直接验证 tcslib.BTN_FMT 与那个集合推导式的行为。只读。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T

print('BTN_FMT    = %r  (len=%d)' % (T.BTN_FMT, len(T.BTN_FMT)))
print('BTN_RE.pattern = %r' % T.BTN_RE.pattern)
text = 'SD \ue0af MP5'
print('text = %r' % text)
s = {T.BTN_FMT % ord(c) for c in text if 0xE000 <= ord(c) <= 0xE0FF}
print('集合推导式结果 = %r  (type=%s)' % (s, type(s).__name__))
for c in text:
    if 0xE000 <= ord(c) <= 0xE0FF:
        print('  c=%r ord=%d  BTN_FMT %% ord = %r' % (c, ord(c), T.BTN_FMT % ord(c)))
print('sorted 后 = %r' % sorted(s))
