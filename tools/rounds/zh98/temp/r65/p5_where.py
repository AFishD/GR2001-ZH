# -*- coding: utf-8 -*-
r"""p5_where.py — 实拍窗口起点 "蓝蔽薄藏…" 在整段测试文本里排第几行?
判据: 若它在很靠后的位置 ⇒ 页面初始滚动**不在开头**。"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                             # noqa: E402

P = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r63', 'tp_unicode_report.json')
r = json.load(io.open(P, encoding='utf-8'))
print('report = %s' % P)
print('order=%s, text=%s' % (r.get('order'), json.dumps(r.get('text'), ensure_ascii=False)))
print('text_head = %r' % r.get('text_head', '')[:80])

cs = tcslib.Charset()
enc = {}
for ch, (b1, b2) in cs.enc_pair.items():
    enc[ch] = bytes((b1, b2))
for ch, b in cs.enc_single.items():
    enc[ch] = bytes((b,))
chars = (sorted(enc, key=ord) if r.get('order') == 'unicode'
         else sorted(enc, key=lambda c: (enc[c], c)))
cols = r['text']['cols']
page_lines = r['text']['page_lines']
parts = [r['text']['header'], '{p}']
nl = 0
for i, ch in enumerate(chars):
    parts.append(ch)
    if i == len(chars) - 1:
        break
    if (i + 1) % cols == 0:
        nl += 1
        parts.append('{p}' if (page_lines and nl % page_lines == 0) else '{br}')
text = ''.join(parts)
probe = '蓝蔽薄藏虏虽蛋蜂螺血行衍衔'
k = text.find(probe)
print('全文 %d 字符; "蓝蔽薄藏…" @%d' % (len(text), k))
if k >= 0:
    before = text[:k]
    print('它之前有 %d 个 {br}/{p} 标记 ⇒ 视觉行号 ≈ %d'
          % (len(re.findall(r'\{(?:br|p)\}', before)),
             len(re.findall(r'\{(?:br|p)\}', before))))
    print('它之前的原文 = %r' % before[-70:])
print('text_tail = %r' % text[-60:])
