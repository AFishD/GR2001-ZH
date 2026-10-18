# -*- coding: utf-8 -*-
"""r50 临时: 对比 round46 重排 前后 的 charset, 找出**槽位变了的字**。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                          # noqa: E402

A = json.load(io.open(os.path.join(REPO, 'work/builds/GR_ZH95/temp/font_repack/charset_before.json'),
                      encoding='utf-8'))['pair_of']
B = json.load(io.open(os.path.join(REPO, 'work/builds/GR_ZH95/temp/r46/charset_after_repack.json'),
                      encoding='utf-8'))['pair_of']
print('before pair=%d after pair=%d' % (len(A), len(B)))
print('只在 before:', ''.join(sorted(set(A) - set(B)))[:80])
print('只在 after :', ''.join(sorted(set(B) - set(A)))[:80])
moved = []
for ch in sorted(set(A) & set(B)):
    if tuple(A[ch]) != tuple(B[ch]):
        moved.append((ch, tuple(A[ch]), tuple(B[ch]),
                      tcslib.pair_slot(*A[ch]), tcslib.pair_slot(*B[ch])))
print('槽位/码位发生变化的字: %d 个' % len(moved))
for ch, a, b, sa, sb in moved:
    print('   %s  %02X%02X(slot %4d row%2d col%2d) -> %02X%02X(slot %4d row%2d col%2d)  Δslot=%+d'
          % (ch, a[0], a[1], sa, sa // 62, sa % 62, b[0], b[1], sb, sb // 62, sb % 62, sb - sa))
