# -*- coding: utf-8 -*-
r"""r58 探针8: 登记容器"重压后会不会超槽" (只读) —— 决定能不能就地重编码。

对每个候选容器: 解出 blob, 用 tcslib.lzo_compress(level=7) 逐子流重压, 比较总帧长与槽位。
"""
import os
import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso'))
TARGETS = [('MENU.IMG', 30), ('GR.IMG', 903), ('MENU.IMG', 25), ('GR.IMG', 902),
           ('MENU.IMG', 283), ('MENU.IMG', 26), ('GR.IMG', 900), ('MENU.IMG', 27),
           ('GR.IMG', 904), ('MENU.IMG', 28), ('GR.IMG', 907), ('MENU.IMG', 29),
           ('GR.IMG', 910), ('MENU.IMG', 285), ('GR.IMG', 4059), ('MENU.IMG', 286),
           ('GR.IMG', 4061), ('MENU.IMG', 284), ('GR.IMG', 4057), ('MENU.IMG', 32),
           ('GR.IMG', 905), ('MENU.IMG', 33), ('GR.IMG', 908), ('GR.IMG', 4062)]
print('%-34s %-6s %-9s %-9s %-9s %-9s %s' %
      ('container', 'mode', 'slot', 'subs', '原帧长', '重压帧长', '余量'))
t0 = time.time()
for (tag, idx) in TARGETS:
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    s = FC.Slot(iso, tag, lba, idx)
    if s.mode != 'lzo':
        print('%-34s %-6s %-9d %s' % ('%s#%d %s' % (tag, idx, s.name), s.mode, s.slot, '(raw)'))
        continue
    frame = bytearray()
    for k, S in enumerate(s.sizes):
        c = s.blob[sum(s.sizes[:k]):sum(s.sizes[:k]) + S]
        cc = tcslib.lzo_compress(c, level=7, use_m1=True, use_m4=True)
        frame += struct.pack('<II', len(cc), S) + cc
    print('%-34s %-6s %-9d %-9d %-9d %-9d %+d'
          % ('%s#%d %s' % (tag, idx, s.name), s.mode, s.slot, len(s.sizes), len(s.raw),
             len(frame), s.slot - len(frame)))
print('%.0fs' % (time.time() - t0))
iso.close()
