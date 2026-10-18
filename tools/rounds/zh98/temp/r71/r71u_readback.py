# -*- coding: utf-8 -*-
r"""r71u_readback.py — 门禁② 逐条回读 == 表 ; 并解释 T0045/T0049 为何也在改写集里"""
import csv
import io
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
INJ = os.path.join(HERE, 'inject')
DUMP = os.path.join(REPO, 'work', 'builds', 'GR_ZH113_B', 'text')
T113 = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402
WRAP = T.WRAP_RE                    # ★ 权威口径: r'\{(?:WRAP|WARP)\}', re.I (两种拼写!)


def canon(t):
    """把 {WRAP} 与真换行归一成同一种写法, 便于比较。"""
    return WRAP.sub('\n', t or '')


print('===== 门禁② 逐条回读 == 表 =====')
tot = ok = 0
bad = []
for kind in ('long', 'long_nowrap', 'short'):
    a = {r['id']: r for r in csv.DictReader(
        io.open(os.path.join(INJ, 'GR_ZH113b_text_%s.csv' % kind), encoding='utf-8-sig', newline=''))}
    b = {r['id']: r for r in csv.DictReader(
        io.open(os.path.join(DUMP, 'GR_ZH113_B_text_%s.csv' % kind), encoding='utf-8-sig', newline=''))}
    n = 0
    for i, ra in a.items():
        tot += 1
        rb = b.get(i)
        if rb is None:
            bad.append((kind, i, '盘上没有'))
            continue
        if canon(ra['text_edited']) == canon(rb['text_zh']) == canon(rb['text_edited']):
            ok += 1
        else:
            n += 1
            bad.append((kind, i, '不一致'))
    print('  %-12s %d 行, 回读一致 %d, 不一致 %d' % (kind, len(a), len(a) - n, n))
print('  合计 %d / %d 一致 %s' % (ok, tot, '✓' if ok == tot else '✗'))
for x in bad[:20]:
    print('    [!!] %s' % (x,))

print()
print('===== T0045 / T0049 为何也在改写集里 =====')
for eid in ('SFXML:T0045', 'SFXML:T0049'):
    A = {r['id']: r for r in csv.DictReader(
        io.open(os.path.join(T113, 'GR_ZH113_text_long.csv'), encoding='utf-8-sig', newline=''))}[eid]
    B = {r['id']: r for r in csv.DictReader(
        io.open(os.path.join(INJ, 'GR_ZH113b_text_long.csv'), encoding='utf-8-sig', newline=''))}[eid]
    print('-- %s' % eid)
    print('   现役(GR_ZH113) : %s' % canon(A['text_edited']).replace('\n', '⏎')[:160])
    print('   本轮(丰富版)   : %s' % canon(B['text_edited']).replace('\n', '⏎')[:160])
    print('   相同: %s' % (canon(A['text_edited']) == canon(B['text_edited'])))
