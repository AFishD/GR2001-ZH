# -*- coding: utf-8 -*-
r"""zero_pak.py — 列出 COMMON.PAK（MENU.IMG 条目 #3）里的全部记录名 + 字段（只读）

背景: GetTexture(name) 先 `GetName(RSFilename)`（去扩展名）到 UITextureMgr 的名字表里查
      （FindSurface），命中就**直接返回已有纹理**、不发起读盘。
      历史实验 F4 把 FONT.RES 的贴图名改成 `LOAD_NEW_1.RSB` ⇒ 若 COMMON.PAK 里本来就有
      一条叫 `load_new_1` 的纹理（开机转轮图），就会命中已有纹理 ⇒ **cdvd 零读取**。
      本脚本用来证实/否证这条解释。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
MENU_LBA, MENU_SIZE = 776286, 58300882
base = MENU_LBA * 2048
e = iso.img_entry(MENU_LBA, 3)
print('MENU.IMG #3 = %r off=0x%X stored=%d real=%d' % (e['name'], e['off'], e['stored'], e['real']))
pak = iso.read(base + e['off'], e['stored'])
print('COMMON.PAK %d B; 前 16 字节 %s' % (len(pak), pak[:16].hex(' ')))

LS = []
q = 0
n = 0
while q + 8 <= len(pak):
    mode, nl = struct.unpack_from('<II', pak, q)
    if nl < 1 or nl > 64 or q + 8 + nl > len(pak):
        LS.append('  !! 解析中断 @0x%X mode=%d nl=%d' % (q, mode, nl))
        break
    nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
    r = q + 8 + nl
    if mode == 0:
        psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
        r2 = r + 16 + clut
        if r2 + 4 > len(pak):
            LS.append('  !! mode0 字段越界 @0x%X' % q)
            break
        px = struct.unpack_from('<I', pak, r2)[0]
        end = r2 + 4 + px
        LS.append('  #%-3d @0x%06X %-26r mode=0 psm=0x%02X %dx%d clut=0x%X px=0x%X end=0x%X'
                  % (n, q, nm, psm, w, h, clut, px, end))
        q = end
    elif mode == 2:
        LS.append('  #%-3d @0x%06X %-26r mode=2 (8bpp? 见反编译)' % (n, q, nm))
        # mode2: read 4 (psm), 4(w), 4(h); if psm in {0x13,0x14}: 4 clut_size + clut; then 4 px + px
        psm, w, h = struct.unpack_from('<III', pak, r)
        r2 = r + 12
        if psm in (0x13, 0x14):
            cz = struct.unpack_from('<I', pak, r2)[0]
            r2 += 4 + cz
        px = struct.unpack_from('<I', pak, r2)[0]
        end = r2 + 4 + px
        q = end
    elif mode == 3:
        LS.append('  #%-3d @0x%06X %-26r mode=3' % (n, q, nm))
        px = struct.unpack_from('<I', pak, r + 0)[0]
        q = r + 4 + px
    else:
        LS.append('  #%-3d @0x%06X %-26r mode=%d （未知，停）' % (n, q, nm, mode))
        break
    n += 1
    if q == len(pak):
        LS.append('  == 正好走到文件尾 (%d B)' % len(pak))
        break
LS.append('记录数 %d, 解析到 0x%X / 0x%X' % (n, q, len(pak)))
txt = '\n'.join(LS)
print(txt)
open(os.path.join(OUT, 'common_pak_records.txt'), 'w', encoding='utf-8').write(txt + '\n')

# 关键判定
names = [l.split('%r' % ()) for l in []]  # noqa
low = txt.lower()
print()
print('=== F4 假设判定 ===')
for probe in ('load_new_1', 'load_new_2'):
    print('  COMMON.PAK 里有 %-12r ? %s' % (probe, '★ 有' if probe in low else '没有'))
iso.close()
