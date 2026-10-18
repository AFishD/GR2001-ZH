# -*- coding: utf-8 -*-
r"""m14_charset.py — round47 ⑭: 现役 charset 与"重排前"备份的差异 (判断单字节码有没有被动过)。"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                             # noqa: E402

CUR = tcslib.CHARSET
BAK = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
cur = json.load(io.open(CUR, encoding='utf-8'))
bak = json.load(io.open(BAK, encoding='utf-8'))
print('现役: %s (%d B)' % (os.path.relpath(CUR, REPO), os.path.getsize(CUR)))
print('备份: %s (%d B)' % (os.path.relpath(BAK, REPO), os.path.getsize(BAK)))

c1, c2 = cur['codes'], bak['codes']
print()
print('单字节码表: 现役 %d 条 / 备份 %d 条' % (len(c1), len(c2)))
diff = [(ch, c2.get(ch), c1.get(ch)) for ch in set(c1) | set(c2)
        if c1.get(ch) != c2.get(ch)]
print('  差异 %d 条: %s' % (len(diff), diff[:20]))

for ch in ('中', '斗', '抖', '的', '你', '聚', '米'):
    print('  %s: 备份单字节=%s 现役单字节=%s | 备份对偶=%s 现役对偶=%s'
          % (ch, bak['codes'].get(ch), cur['codes'].get(ch),
             bak['pair_of'].get(ch), cur['pair_of'].get(ch)))

p1, p2 = cur['pair_of'], bak['pair_of']
d2 = [(ch, p2.get(ch), p1.get(ch)) for ch in set(p1) | set(p2) if p1.get(ch) != p2.get(ch)]
print()
print('对偶码表差异: %d 条 (前 12): %s' % (len(d2), d2[:12]))
moved = [ch for ch, a, b in d2 if a and b]
print('  两版都有但槽位变了: %d 个' % len(moved))
print('  只有备份有: %s' % [ch for ch, a, b in d2 if a and not b][:20])
print('  只有现役有: %s' % [ch for ch, a, b in d2 if b and not a][:20])
print()
print('★ 结论: 单字节码表 %s' % ('未变 ⇒ 单字节字形位置/映射不受重排影响'
                                if not diff else '**变了** ⇒ 必须用备份 charset 才能对上 ZH94 盘'))
