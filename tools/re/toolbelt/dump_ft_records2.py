# -*- coding: utf-8 -*-
r"""dump_ft_records2.py — 用执行任务的权威解析器(zx_lib.ft_records) dump FONT.RES 记录
记录格式: 10 字节, struct '<BB4H' = (b0, b1, u0, u1, u2, u3)
目标: 确认"矩形"4 分量在哪、单位为何、能否指向任意坐标（FT 记录路线的前提）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib      # noqa: E402
import zx_lib      # noqa: E402

MENU_LBA = 776286


def expanded(path):
    iso = tcslib.Iso(os.path.join(REPO, path))
    e = iso.img_entry(MENU_LBA, 4)
    slot = iso.read(e['iso_off'], e['stored'])
    iso.close()
    return b''.join(s[0] for s in tcslib.lzo_subs(slot))


ex = expanded('work/builds/GR_ZH113b/GR_ZH113b.iso')
print('展开 %d B' % len(ex))
faces, endp = zx_lib.ft_records(ex, 28)
print('面数 %d ; 风格/记录区结束 = 0x%X' % (len(faces), endp))
print()
for name, fld, rows in faces:
    print('面 %-8s fld=%s ⇒ nrec=%d ; 记录 %d 条' % (name, fld, fld[4] * fld[5], len(rows)))
    for off, r in rows[:6]:
        b0, b1, u0, u1, u2, u3 = r
        print('   @0x%04X  b0=%3d b1=%3d  u16=(%5d,%5d,%5d,%5d)  hex=%s' % (
            off, b0, b1, u0, u1, u2, u3, ex[off:off + 10].hex()))
    print('   … 末 3 条:')
    for off, r in rows[-3:]:
        b0, b1, u0, u1, u2, u3 = r
        print('   @0x%04X  b0=%3d b1=%3d  u16=(%5d,%5d,%5d,%5d)  hex=%s' % (
            off, b0, b1, u0, u1, u2, u3, ex[off:off + 10].hex()))
    print()
print('⇒ 若 4 个 u16 里有一组 (x,y,w,h) 且能覆盖到任意坐标 ⇒ **矩形可任意指定** ✓（FT 路线可行 ✓）')
print('   否则若它们是固定 16×16 网格的 (col,row) 编码 ⇒ 仍受网格约束 ✗')
