# -*- coding: utf-8 -*-
"""show_block.py <file> <substr> [maxchars] —— 打印 B_funcfixed.txt 里匹配的段"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = sys.argv[1]
key = sys.argv[2]
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
txt = open(p, encoding='utf-8').read()
blocks = re.split(r'^(?===== )', txt, flags=re.M)
n = 0
for b in blocks:
    head = b.split('\n', 1)[0]
    if key in head:
        n += 1
        print(b[:mx])
        if len(b) > mx:
            print('   ... [该段共 %d 字符, 已截断]' % len(b))
        print()
if not n:
    print('(no block matched %r)' % key)
