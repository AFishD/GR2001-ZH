# -*- coding: utf-8 -*-
r"""r71g_apply.py — 把 r71_repl.tsv 的替换应用到 16 条低精准度条目上, 并逐条自查

口径:
  · 底本 = work/builds/GR_ZH109/text_backup_before_wrapfix/GR_ZH109_text_long.csv 的 text_edited
           (先做 wrapfix: (?:\{WRAP\}){2,} → \n\n)
  · 可用字集 = charset_compiled_zh16.json 的 pair_of + codes (1614) + ASCII 可打印
  · 每条替换必须: 在该条正文里**恰好出现 1 次**; `new` 里不得含超范围字; old/new 都不含 {WRAP}/换行
输出:
  · work/builds/GR_ZH98/temp/r71/r71_repl_check.txt     (逐条报告)
  · work/builds/GR_ZH98/temp/r71/r71_reduced_long.csv   (改好的 long 表, 供落盘)
  · work/builds/GR_ZH98/temp/r71/r71_reduce_map.csv     (交付给用户的对照表)
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
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix',
                   'GR_ZH109_text_long.csv')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
TSV = os.path.join(HERE, 'r71_repl.tsv')
TSV_HI = os.path.join(HERE, 'r71_repl_hi.tsv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
HAVE = set(c['pair_of']) | set(c['codes']) | set(chr(i) for i in range(0x20, 0x7F))
WRAP = re.compile(r'\{[Ww][Aa][Rr][Pp]\}')
WRAPS = re.compile(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}')

LOW = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]


def wrapfix(t):
    return WRAPS.sub('\n\n', t or '')


def miss(t):
    t = WRAP.sub('', t)
    return [ch for ch in t if ord(ch) >= 0x80 and ch not in HAVE]


rows = list(csv.DictReader(io.open(SRC, encoding='utf-8-sig', newline='')))
base = {r['id']: wrapfix(r['text_edited']) for r in rows}
orig = dict(base)

# 读替换表
repl = []
for tsv, scene in ((TSV, 'low'), (TSV_HI, 'hi')):
    with io.open(tsv, encoding='utf-8', newline='') as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) != 4:
                raise SystemExit('!! %s 第 %d 行列数不是 4: %r' % (tsv, ln, line[:80]))
            repl.append(dict(id=parts[0], old=parts[1], new=parts[2], method=parts[3],
                             scene=scene, line=ln, src=os.path.basename(tsv)))

print('替换条目: %d 行; 覆盖条目 %d 个' % (len(repl), len(set(r['id'] for r in repl))))

errors = []
maplist = []
for r in repl:
    eid, old, new = r['id'], r['old'], r['new']
    t = base.get(eid)
    if t is None:
        errors.append('第%d行: 找不到条目 %s' % (r['line'], eid))
        continue
    if WRAP.search(old) or WRAP.search(new) or '\n' in old or '\n' in new:
        errors.append('第%d行: 片段含 {WRAP}/换行, 不允许 (%s)' % (r['line'], eid))
        continue
    n = t.count(old)
    if n != 1:
        errors.append('第%d行: %s 里 "%s" 出现 %d 次 (要求 1 次)' % (r['line'], eid, old, n))
        continue
    bad_new = miss(new)
    if bad_new:
        errors.append('第%d行: %s 改后片段仍含超范围字 %s -> %s'
                      % (r['line'], eid, ''.join(bad_new), new))
        continue
    removed = miss(old)
    if not removed:
        errors.append('第%d行: %s 的原文片段 "%s" 本来就没有超范围字 (多余替换)'
                      % (r['line'], eid, old))
        continue
    base[eid] = t.replace(old, new, 1)
    maplist.append(dict(id=eid, old=old, new=new, chars=''.join(removed),
                        n_chars=len(removed), method=r['method'], scene=r['scene']))

if errors:
    print('\n!! 有 %d 处问题, 未应用:' % len(errors))
    for e in errors:
        print('   ' + e)
    raise SystemExit(1)

print('全部替换校验通过, 已应用 %d 处' % len(maplist))

# ---- 逐条自查 ----
print('\n===== 逐条自查 (16 条低精准度) =====')
left = {}
for eid in LOW:
    m = miss(base[eid])
    left[eid] = m
    print('  %-14s 原文缺 %3d 种 / %4d 次  ->  改后缺 %3d 种 / %4d 次  %s'
          % (eid, len(set(miss(orig[eid]))), len(miss(orig[eid])), len(set(m)), len(m),
             ('剩余: ' + ''.join(sorted(set(m)))) if m else 'OK'))
tot_k = set()
tot_n = 0
for eid in LOW:
    tot_k |= set(left[eid])
    tot_n += len(left[eid])
print('  16 条合计剩余: %d 种 / %d 次' % (len(tot_k), tot_n))
print('  替换处数: %d (低精准度 %d + 高精准度 %d)'
      % (len(maplist), sum(1 for x in maplist if x['scene'] == 'low'),
         sum(1 for x in maplist if x['scene'] == 'hi')))
print('  消除字样 %d 种 / %d 次'
      % (len(set(''.join(x['chars'] for x in maplist))), sum(x['n_chars'] for x in maplist)))

print('\n===== 逐条自查 (9 条高精准度 特别收录其它) =====')
HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044',
      'SFXML:T0046', 'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']
hi_left = 0
for eid in HI:
    m = miss(base[eid])
    hi_left += len(m)
    print('  %-14s -> 改后缺 %3d 种 / %4d 次  %s'
          % (eid, len(set(m)), len(m), ('剩余: ' + ''.join(sorted(set(m)))) if m else 'OK'))

# ---- 全表统计 ----
allk = Counter()
for eid, t in base.items():
    for ch in miss(t):
        allk[ch] += 1
print('\n===== long 表 58 条整体 =====')
print('  改后全表缺字: %d 种 / %d 次' % (len(allk), sum(allk.values())))
hi = {ch: n for ch, n in allk.items() if ch not in tot_k}
print('  其中**高精准度条目**里的缺字: %d 种 / %d 次 : %s'
      % (len(hi), sum(hi.values()), ''.join(sorted(hi))))

# ---- 写盘: 改后的 long 表 ----
out_csv = os.path.join(HERE, 'r71_reduced_long.csv')
with io.open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\r\n')
    w.writeheader()
    for r in rows:
        r2 = dict(r)
        if r['id'] in base:
            r2['text_edited'] = base[r['id']]
        w.writerow(r2)
print('\n-> %s' % out_csv)

# ---- 对照表 ----
mp = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71', 'r71_reduce_map.csv')
with io.open(mp, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['条目id', '原文片段', '改后片段', '替换了哪些超范围字', '字数', '手法'])
    for x in maplist:
        w.writerow([x['id'], x['old'], x['new'], x['chars'], x['n_chars'], x['method']])
print('-> %s' % mp)

# ---- 逐条报告 ----
with io.open(os.path.join(HERE, 'r71_repl_check.txt'), 'w', encoding='utf-8', newline='\n') as f:
    cur = None
    for x in maplist:
        if x['id'] != cur:
            cur = x['id']
            f.write('\n' + '#' * 90 + '\n### %s\n' % cur)
        f.write('  %s\n    -> %s   [%s]  %s\n' % (x['old'], x['new'], x['chars'], x['method']))
print('-> %s' % os.path.join(HERE, 'r71_repl_check.txt'))
