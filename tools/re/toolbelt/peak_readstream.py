# -*- coding: utf-8 -*-
r"""peak_readstream.py — 读任意 cdvd.log 的最大 LBA / 最后读 / 停读帧号"""
import glob
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = sys.argv[1]
cands = glob.glob(os.path.join(REPO, d, '**', 'cdvd.log'), recursive=True)
if not cands:
    print('  未找到 cdvd.log in %s' % d); sys.exit(0)
p = cands[0]
rows = []
with open(p, 'r', errors='replace') as f:
    for ln in f:
        t = ln.split()
        if len(t) >= 2:
            try:
                rows.append((int(t[0]), int(t[1])))
            except ValueError:
                pass
print('  %s' % p.replace(REPO + '\\', ''))
print('  读盘事件 %d 条' % len(rows))
if rows:
    mx = max(r[1] for r in rows)
    print('  最大 LBA = %d' % mx)
    print('  最后 5 次 (frame,lba) = %s' % rows[-5:])
    # 停读帧号: 最后一次出现 maxLBA 的 frame
    lastmax = max(r[0] for r in rows if r[1] == mx)
    print('  最后一次最大 LBA 的帧 = %d' % lastmax)
    print('  该帧之后还有 %d 条读盘事件' % sum(1 for r in rows if r[0] > lastmax))
print('  对照: 可用盘 maxLBA 804733 ; W2048 失败盘 776669 (=PAK起+209扇区=428032B 处停)')
