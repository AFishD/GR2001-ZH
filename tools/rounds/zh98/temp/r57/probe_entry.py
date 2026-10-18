# -*- coding: utf-8 -*-
r"""r57 探针2: GR.IMG 条目表里 iso_off 落在 0x1F035800..0x1F635800 的条目 (只读)。"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
iso = tcslib.Iso(ISO)
GR = 19175
LO, HI = 0x1F035800, 0x1F635800
base = GR * 2048
noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
names = [x.decode('latin-1') for x in bytes(iso.mm[base + noff:base + nend]).split(b'\x00') if x]
print('GR.IMG 名字 %d 个 (名字表 0x%X..0x%X)' % (len(names), noff, nend))
# 条目表紧跟在 "GR.IMG\0" 之后? 用前 16 个名字的长度和定位 (同样品里 repack 的做法)
e0 = 0x18 + 8                                        # 'GR.IMG\0' = 8 字节
off_tbl = base + e0 + sum(len(x) + 1 for x in names)  # 名字区之后 = 条目表
print('推测条目表 @0x%X (基址+0x%X)' % (off_tbl, off_tbl - base))
hit = []
for i in range(len(names)):
    o, s, r, nmoff = struct.unpack_from('<IIII', iso.mm, off_tbl + 16 * i)
    io_off = o * 2048
    if LO - 0x400000 <= io_off < HI + 0x400000:
        hit.append((i, names[i], o, s, r, io_off))
for (i, nm, o, s, r, io_off) in hit:
    print('  #%-5d %-28s LBA %-9d stored 0x%-8X real 0x%-8X iso_off 0x%X..0x%X %s'
          % (i, nm, o, s, r, io_off, io_off + s, '★ 命中' if io_off <= LO < io_off + s else ''))
print('\n条目表前后裸字节 (0x%X):' % (off_tbl - base))
print(bytes(iso.mm[off_tbl:off_tbl + 64]).hex(' '))
iso.close()
