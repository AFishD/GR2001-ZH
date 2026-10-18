# -*- coding: utf-8 -*-
r"""r71h_probe.py — 逐个候选词查可用性: 读 r71_cand.txt (每行一个词), 打印不在字库的字符"""
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
HAVE = set(c['pair_of']) | set(c['codes']) | set(chr(i) for i in range(0x20, 0x7F))

for w in io.open(os.path.join(HERE, 'r71_cand.txt'), encoding='utf-8'):
    w = w.strip()
    if not w:
        continue
    bad = sorted(set(ch for ch in w if ord(ch) >= 0x80 and ch not in HAVE))
    print('%-24s %s' % (w, ('OK' if not bad else '缺: ' + ''.join(bad))))
