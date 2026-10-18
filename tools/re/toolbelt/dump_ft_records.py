# -*- coding: utf-8 -*-
r"""dump_ft_records.py — 从盘上解出 FONT.RES 展开态(5942 B)的风格/记录表结构

已知: 风格/记录表在展开态 **0x1620** 起；记录 10 字节/条；nrec = fld[4]*fld[5]；
      faces 名: large / default / huge；nrec 224 / 224 / 96
本脚本: 逐字段 dump，确认结构并给出每条记录的原始 10 字节（供新路线设计用）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286


def expanded(path):
    iso = tcslib.Iso(os.path.join(REPO, path))
    e = iso.img_entry(MENU_LBA, 4)          # #4 = FONT.RES
    slot = iso.read(e['iso_off'], e['stored'])
    iso.close()
    subs = tcslib.lzo_subs(slot)
    return b''.join(s[0] for s in subs)


for tag, path in (('113b', 'work/builds/GR_ZH113b/GR_ZH113b.iso'),
                  ('121', 'work/builds/GR_ZH121/GR_ZH121.iso')):
    ex = expanded(path)
    print('=== %s: FONT.RES 展开 %d B ===' % (tag, len(ex)))
    # faces 区: 头部 12B + NUL 名 + NUL 名 + ... 到 0x1620
    i = 12
    names = []
    while i < 0x1620 and ex[i] != 0:
        j = ex.index(b'\x00', i)
        names.append(ex[i:j].decode('latin1'))
        i = j + 1
    print('  名字: %s' % names)
    print('  [0x1620 起] 表头:')
    off = 0x1620
    for k in range(8):
        v = struct.unpack_from('<I', ex, off + 4 * k)[0]
        print('    +0x%03X = %d (0x%X)' % (4 * k, v, v))
    print()
    # 按 nrec = fld[4]*fld[5] 找记录表
    f4 = struct.unpack_from('<I', ex, off + 16)[0]
    f5 = struct.unpack_from('<I', ex, off + 20)[0]
    print('  fld[4]=%d fld[5]=%d ⇒ nrec=%d' % (f4, f5, f4 * f5))
    print('  表头后 40 字节 hex: %s' % ex[off:off + 40].hex())
    print()
    # 记录样例: 从 off+? 找 10 字节步进里像矩形的数据
    print('  在 0x1620..0x1700 里以 10 字节步进的第一批记录（x,y,w,h 猜想）:')
    for rec in range(0x1620, 0x1620 + 10 * 8, 10):
        b = ex[rec:rec + 10]
        u = struct.unpack('<5H', b)
        print('    @0x%04X  %s  → u16: %s' % (rec, b.hex(), u))
    print()
