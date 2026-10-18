# -*- coding: utf-8 -*-
r"""check_w2048_lengths.py — 核对 W=2048 实验盘的三处长度是否自洽
① COMMON.PAK 条目 stored/real/off（应随新容器长大）
② new_font_revised 记录: W(+0x01C) / h(+0x020) / px_size(+0x438)
③ 与 GR_ZH123（可用盘）对照
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286
REC = 0x1031

for tag, path in (('GR_ZH123(可用)', 'work/builds/GR_ZH123/GR_ZH123.iso'),
                  ('W2048(黑屏)', 'work/builds/GR_TEST_W2048/GR_TEST_W2048.iso')):
    p = os.path.join(REPO, path)
    if not os.path.exists(p):
        print('=== %s: 盘不存在 %s ===' % (tag, path))
        continue
    iso = tcslib.Iso(p)
    print('=== %s ===' % tag)
    for i in range(8):
        try:
            e = iso.img_entry(MENU_LBA, i)
        except Exception as ex:
            print('  #%d 读取异常 %s' % (i, ex)); break
        if 'COMMON' in e['name'].upper():
            pak = e
        print('  #%d %-28s stored=%-10d real=%-10d off=0x%X' % (i, e['name'], e['stored'], e['real'], e['off']))
    raw = iso.read(pak['iso_off'], pak['stored'])
    w, h, clut = struct.unpack_from('<3I', raw, REC + 0x1C)
    px = struct.unpack_from('<I', raw, REC + 0x438)[0]
    print('  --> PAK: stored=%d real=%d off=0x%X' % (pak['stored'], pak['real'], pak['off']))
    print('  --> 记录: W=%d h=%d clut=0x%X px_size=0x%X (%d)' % (w, h, clut, px, px))
    print('      期望: px_size == W*h/2 + 16 = %d' % (w * h // 2 + 16))
    print('      容器实际可用 = stored(PAK) 里扣掉非容器部分 ⇒ 需 stored >= 记录的 px_size')
    print('      ★ stored - px_size = %d  %s' % (pak['stored'] - px,
          '(>=0 ✓ 长度自洽)' if pak['stored'] >= px else '(**<0 ✗ 声明的像素数据比 PAK 能给的还大 ⇒ 引擎读不满 ⇒ 卡死** )'))
    iso.close()
    print()
