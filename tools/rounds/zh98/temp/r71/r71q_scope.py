# -*- coding: utf-8 -*-
r"""r71q_scope.py — 范围自查: 本轮到底改了什么 (门禁③)

① 对比「恢复后的丰富版底本」vs「本轮产物」: 必须**只有** 16+9=25 条不同, 其余 33 条逐字节一致
② 对比 GR_ZH113 现役 long 表: 列出本轮变化的条目 (应 = 58 条, 因为整表换回丰富版)
③ nowrap / short 两表: 与 GR_ZH113 现役**逐字节一致** (sha256 相同)
④ {WRAP} 标记合法性: 不在开头/末尾/不紧邻另一个标记/不紧邻换行 (tcslib 权威口径)
"""
import csv
import io
import json
import os
import re
import sys
import hashlib

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
INJ = os.path.join(HERE, 'inject')
BAK = os.path.join(HERE, 'text_backup_before_r71')
T113 = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p):
    h = hashlib.sha256()
    with io.open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return {r['id']: r for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline=''))}


base = load(os.path.join(BAK, 'GR_ZH113b_text_long.csv'))
new = load(os.path.join(INJ, 'GR_ZH113b_text_long.csv'))
old = load(os.path.join(T113, 'GR_ZH113_text_long.csv'))

diff = [i for i in base if base[i]['text_edited'] != new[i]['text_edited']]
same = [i for i in base if base[i]['text_edited'] == new[i]['text_edited']]
print('① 丰富版底本 -> 本轮产物:')
print('   不同条目 %d 个: %s' % (len(diff), ' '.join(sorted(diff))))
print('   完全未动 %d 个 (逐字节一致) ✓' % len(same))
diff2 = [i for i in old if old[i]['text_edited'] != new[i]['text_edited']]
print('② 对比 GR_ZH113 现役 long 表: 变化 %d / %d 条' % (len(diff2), len(old)))
same2 = sorted(set(old) - set(diff2))
if same2:
    print('   与现役完全相同的条目: %s' % ' '.join(same2))

print('③ nowrap / short 两表 vs 现役:')
for k in ('long_nowrap', 'short'):
    p1 = os.path.join(INJ, 'GR_ZH113b_text_%s.csv' % k)
    p2 = os.path.join(T113, 'GR_ZH113_text_%s.csv' % k)
    s1, s2 = sha(p1), sha(p2)
    print('   %-12s %s  %s' % (k, '逐字节一致 ✓' if s1 == s2 else '不同 ✗', s1[:16]))

print('④ {WRAP} 标记合法性 (tcslib 权威口径):')
bad = 0
for i, r in sorted(new.items()):
    t = r['text_edited'] or ''
    _clean, mbad = T.scan_wrap_marks(t)
    pl = T.scan_wrap_placement(t)
    n = len(T.WRAP_RE.findall(t))
    if mbad or pl:
        bad += 1
        print('   %-14s 写法问题=%s 位置问题=%s' % (i, mbad, pl))
print('   有问题条目 %d 个 %s' % (bad, '✓' if bad == 0 else '✗'))
nw = sum(len(T.WRAP_RE.findall(r['text_edited'] or '')) for r in new.values())
print('   {WRAP} 总数: %d' % nw)
print('   含换行条目: %d' % sum(1 for r in new.values() if '\n' in (r['text_edited'] or '')))
