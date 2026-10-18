# -*- coding: utf-8 -*-
r"""r71v_t0010.py — 定位 SFXML:T0010 回读不一致的第一个字符"""
import csv
import io
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WRAP = re.compile(r'\{[Ww][Aa][Rr][Pp]\}')


def canon(t):
    return WRAP.sub('\n', t or '')


def row(p, rid):
    for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')):
        if r['id'] == rid:
            return r
    return None


a = row(os.path.join(REPO, 'work/builds/GR_ZH98/temp/r71/inject/GR_ZH113b_text_long.csv'), 'SFXML:T0010')
b = row(os.path.join(REPO, 'work/builds/GR_ZH113_B/text/GR_ZH113_B_text_long.csv'), 'SFXML:T0010')
c = row(os.path.join(REPO, 'work/builds/GR_ZH113/text/GR_ZH113_text_long.csv'), 'SFXML:T0010')

A, B, C = canon(a['text_edited']), canon(b['text_zh']), canon(b['text_edited'])
print('inject.text_edited      len=%d  {WRAP}=%d' % (len(A), len(WRAP.findall(a['text_edited']))))
print('dump.text_zh            len=%d  \\n=%d' % (len(B), B.count('\n')))
print('dump.text_edited        len=%d  \\n=%d  {WRAP}=%d'
      % (len(C), C.count('\n'), len(WRAP.findall(b['text_edited'] or ''))))
print('车过来的 text_edited 原文 == 我表里的? %s' % (b['text_edited'] == a['text_edited']))
print('GR_ZH113 现役 text_edited len=%d' % len(canon(c['text_edited'])))
print()
for nm, X in (('A(inject)', A), ('B(dump.zh)', B), ('C(dump.ed)', C)):
    print('%-12s %r' % (nm, X))
print()
for nm, X in (('B', B), ('C', C)):
    if A != X:
        k = next((i for i in range(min(len(A), len(X))) if A[i] != X[i]), min(len(A), len(X)))
        print('A vs %s 首个不同位置 %d: A=%r %s=%r' % (nm, k, A[max(0, k - 12):k + 12], nm, X[max(0, k - 12):k + 12]))
