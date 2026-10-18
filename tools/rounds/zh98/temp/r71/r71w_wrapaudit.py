# -*- coding: utf-8 -*-
r"""r71w_wrapaudit.py — 审计 wrapfix: 底本里的"紧邻断点标记" vs 产物里的空行

口径 = tcslib.WRAP_RE (权威: 两种拼写 WRAP / WARP, 大小写不限)。
① 底本 (text_backup_before_wrapfix) 里有多少"紧邻标记组"(长度≥2) —— 应全部被修
② 本轮产物里还有没有紧邻标记 (必须 0; 有则注入器会拒)
③ 产物里的空行组数 (= \n\n) 与 ① 的组数一致
④ 与注入报告的 breaks_p 对表
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BAK = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix',
                   'GR_ZH109_text_long.csv')


def groups(t, pat=None):
    """返回"紧邻标记组"的 (起, 长度) 列表"""
    pat = pat or T.WRAP_RE
    out, i, n = [], 0, len(t or '')
    while i < n:
        m = pat.match(t, i)
        if not m:
            i += 1
            continue
        j, k = i, 0
        while j < n:
            m2 = pat.match(t, j)
            if not m2:
                break
            j = m2.end()
            k += 1
        out.append((i, k))
        i = j
    return out


def load(p):
    return {r['id']: (r.get('text_edited') or '') for r in
            csv.DictReader(io.open(p, encoding='utf-8-sig', newline=''))}


bak = load(BAK)
new = load(os.path.join(HERE, 'inject', 'GR_ZH113b_text_long.csv'))

print('① 底本: 标记总数 %d' % sum(len(T.WRAP_RE.findall(t)) for t in bak.values()))
gk = Counter()
rows_pair = 0
pairs_total = 0
for i, t in bak.items():
    g = groups(t)
    multi = [x for x in g if x[1] >= 2]
    if multi:
        rows_pair += 1
        pairs_total += sum(x[1] for x in multi)
    for (_, k) in multi:
        gk[k] += 1
print('   含"紧邻标记组"的条目 %d 个; 组数 %d; 组内标记合计 %d' % (rows_pair, sum(gk.values()), pairs_total))
print('   组长度分布: %s' % dict(sorted(gk.items())))
print('   拼写分布: WRAP(大写序)=%d  WARP(小写序)=%d'
      % (len(re.findall(r'\{(?i:WRAP)\}', ' '.join(bak.values()))),
         len(re.findall(r'\{(?i:WARP)\}', ' '.join(bak.values())))))

print()
print('② 本轮产物: 标记总数 %d' % sum(len(T.WRAP_RE.findall(t)) for t in new.values()))
left = 0
for i, t in new.items():
    g = [x for x in groups(t) if x[1] >= 2]
    if g:
        left += len(g)
        print('   [!!] %s 还有 %d 组紧邻标记' % (i, len(g)))
print('   剩余紧邻标记组: %d %s' % (left, '✓' if left == 0 else '✗'))

print()
print('③ 产物里的空行组 (\\n\\n):')
blank = 0
rows_blank = 0
for i, t in new.items():
    c = len(re.findall(r'\n\n', t))
    if c:
        rows_blank += 1
        blank += c
print('   条目 %d 个 / 空行组 %d 个 (应对上 ①的组数 %d : %s)'
      % (rows_blank, blank, sum(gk.values()),
         '✓' if blank == sum(gk.values()) else '✗'))

print()
print('④ 与注入报告 breaks_p 对表:')
rep = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH113_B', 'temp',
                                    'inject1_report.json'), encoding='utf-8'))
tb = ta = 0
mismatch = []
for r in rep['rows']:
    tb += r.get('breaks_p_before', 0)
    ta += r.get('breaks_p_after', 0)
    want = len(re.findall(r'\n\n', new.get(r['id'], '')))
    got = r.get('breaks_p_after', 0)
    if want != got:
        mismatch.append((r['id'], want, got))
print('   被写条目合计: {p} 前 %d -> 后 %d' % (tb, ta))
print('   与表里空行组不一致的条目: %d %s' % (len(mismatch), '✓' if not mismatch else mismatch))
