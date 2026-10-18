# -*- coding: utf-8 -*-
r"""_dbg_iso_diff.py — 成品 vs 基底 的**差异区段**清单（只读, 用于把全盘差异逐段定性）"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402

A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                       'GR_ZH113b.iso')
Bp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, 'work', 'builds', 'GR_FA2400',
                                                        'GR_FA2400.iso')
MENU_BASE = zx_lib.MENU_LBA * 2048
GR_BASE = zx_lib.GR_LBA * 2048

lab = {}
for (iso_p, tag) in ((A, 'BASE'), (Bp, 'NEW')):
    iso = T.Iso(iso_p)
    for (lba, nm) in ((zx_lib.MENU_LBA, 'MENU.IMG'), (zx_lib.GR_LBA, 'GR.IMG')):
        for e in zx_lib.entries(iso, lba):
            lab[(lba * 2048) + e['off']] = '%s:%s#%d' % (tag, nm, e['idx'])
    iso.close()
print('== 差异区段 (A=%s B=%s)' % (os.path.basename(A), os.path.basename(Bp)))
sa, sb = os.path.getsize(A), os.path.getsize(Bp)
print('   尺寸 %d / %d' % (sa, sb))
runs = []
with open(A, 'rb') as fa, open(Bp, 'rb') as fb:
    pos = 0
    cur = None
    n_in = 0
    while pos < min(sa, sb):
        n = min(1 << 22, min(sa, sb) - pos)
        ba, bb = fa.read(n), fb.read(n)
        if ba != bb:
            for i in range(n):
                if ba[i] != bb[i]:
                    p = pos + i
                    if cur is not None and p == cur[1]:
                        cur[1] = p + 1
                        cur[2] += 1
                    else:
                        if cur:
                            runs.append(cur)
                        cur = [p, p + 1, 1]
        pos += n
    if cur:
        runs.append(cur)
tot = sum(r[2] for r in runs)
print('   差异区段 %d 个 ; 差异字节合计 %d' % (len(runs), tot))
for (s, e, n) in runs:
    # 归属: 找最后一个 <= s 的条目
    key = max((k for k in lab if k <= s), default=None)
    who = lab.get(key, '?') if (key is not None and s - key < (1 << 26)) else '?'
    print('   0x%08X..0x%08X  %8d B   (最近条目 %s @0x%08X, +0x%X)'
          % (s, e, n, who, key or 0, s - (key or 0)))
