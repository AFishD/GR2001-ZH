# -*- coding: utf-8 -*-
r"""p3_pak.py — COMMON.PAK new_font_revised 记录 + GIF 分段实测 (决定 nib 缓冲区大小)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso')
W, H = 1024, 512
iso = tcslib.Iso(ISO)
pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
print('[IMG ] COMMON.PAK off=0x%X stored=0x%X iso_off=%d' % (pak_e['off'], pak_e['stored'], pak_e['iso_off']))
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
for r in tcslib.parse_pak_records(pak):
    print('[PAK ] name=%-22s psm=0x%02X %dx%d clut=%d px_size=%d px_off=0x%X (容器尾=0x%X)'
          % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[6] + r[5]))
    if r[0] == 'new_font_revised':
        psm, w, h, clut, px, PX = r[1], r[2], r[3], r[4], r[5], r[6]
blob = bytes(pak[PX:PX + px])
segs = tcslib.atlas_container_segments(blob, W // 2)
print('[SEG ] 段数=%d' % len(segs))
tot = 0
for k, (row, off, ln) in enumerate(segs):
    print('        seg%d first_row=%-4d doff=0x%-6X len=%6d (%d 行 + %d B)'
          % (k, row, off, ln, ln // (W // 2), ln % (W // 2)))
    tot += ln
print('[SEG ] 数据合计 %d B; 包头 %d B; 容器 %d B; 差 %d' % (tot, len(segs) * 48, len(blob), len(blob) - tot - len(segs) * 48))
print('[SEG ] 末段数据末字节 = 0x%X; 容器末字节 = 0x%X' % (segs[-1][1] + segs[-1][2], len(blob)))
print('[SEG ] W*H//2 = %d' % (W * H // 2))
