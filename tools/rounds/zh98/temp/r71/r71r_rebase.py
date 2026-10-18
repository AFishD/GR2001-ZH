# -*- coding: utf-8 -*-
r"""r71r_rebase.py — 把 r71 产物**挂到 GR_ZH113 现役表的骨架**上

原因: 丰富版底本来自 GR_ZH109 时代的 dump, 它的 offset/len_bytes/max_bytes/text_zh 是
      **GR_ZH109 盘**的口径; 本轮源盘是 GR_ZH113 ⇒ 注入器结构核对照报
      `SFXML:T0028: offset/len 与源盘不符` (exit 1)。
做法: 取 GR_ZH113/text/GR_ZH113_text_long.csv 作骨架 (offset/len_bytes/text_zh 都对),
      只把 text_edited 换成 r71_reduced_long.csv 里同 id 的值; 其余列一字不动。
      同时校对: 两张表的 id 集合必须完全一致; wrap_w/kind 也必须一致。
"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
INJ = os.path.join(HERE, 'inject')
T113 = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

skel_p = os.path.join(T113, 'GR_ZH113_text_long.csv')
src_p = os.path.join(HERE, 'r71_reduced_long.csv')
skel = list(csv.DictReader(io.open(skel_p, encoding='utf-8-sig', newline='')))
src = {r['id']: r for r in csv.DictReader(io.open(src_p, encoding='utf-8-sig', newline=''))}

print('骨架 %d 行; r71 产物 %d 行' % (len(skel), len(src)))
a, b = set(r['id'] for r in skel), set(src)
print('id 集合差: 骨架有而产物没有 %s ; 产物有而骨架没有 %s'
      % (sorted(a - b), sorted(b - a)))
assert a == b, 'id 集合不一致'

n = 0
for r in skel:
    s = src[r['id']]
    if r['text_edited'] != s['text_edited']:
        n += 1
    r['text_edited'] = s['text_edited']
    if r['wrap_w'] != s['wrap_w'] or r['kind'] != s['kind']:
        print('  [警告] %s wrap_w/kind 不同: %s/%s vs %s/%s'
              % (r['id'], r['wrap_w'], r['kind'], s['wrap_w'], s['kind']))
print('text_edited 与现役不同的条目: %d / %d' % (n, len(skel)))

out = os.path.join(INJ, 'GR_ZH113b_text_long.csv')
with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(skel[0].keys()), lineterminator='\r\n')
    w.writeheader()
    for r in skel:
        w.writerow(r)
print('-> %s' % out)

# 同时把"底本"也重新挂一遍 (备份目录里那份也应是 GR_ZH113 骨架 + 丰富版原文, 便于对照)
BAK = os.path.join(HERE, 'text_backup_before_r71')
bak_src = list(csv.DictReader(io.open(os.path.join(BAK, 'GR_ZH113b_text_long.csv'),
                                     encoding='utf-8-sig', newline='')))
bmap = {r['id']: r for r in bak_src}
skel2 = list(csv.DictReader(io.open(skel_p, encoding='utf-8-sig', newline='')))
assert set(bmap) == set(r['id'] for r in skel2)
for r in skel2:
    r['text_edited'] = bmap[r['id']]['text_edited']
out2 = os.path.join(BAK, 'GR_ZH113b_text_long.csv')
with io.open(out2, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(skel2[0].keys()), lineterminator='\r\n')
    w.writeheader()
    for r in skel2:
        w.writerow(r)
print('-> %s (底本, 已挂 GR_ZH113 骨架)' % out2)
