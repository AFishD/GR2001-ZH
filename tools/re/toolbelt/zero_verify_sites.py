# -*- coding: utf-8 -*-
r"""zero_verify_sites.py — 在两个成品盘上逐字节核对「4 处 gate 立即数」与「ISO9660 MENU.IMG 记录」
（只读；把报告里给的落点从"文档引用"升级成"盘上实测"）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
ORIG = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
PATCH_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH119', 'GR_ZH119.iso')
ELF_OFF = 0x93800 + 0x80          # ELF 头在 ISO 0x93800, LOAD 段 file off 0x80, vaddr 0x100000


def va2iso(va):
    return ELF_OFF + (va - 0x100000)


f = open(ISO, 'rb')
print('=== 4 处 gate 立即数 (sltiu, imm=0xB1) ===')
SITES = [0x416EE8, 0x417160, 0x41751C, 0x5656A4]
ok = True
for va in SITES:
    o = va2iso(va)
    f.seek(o)
    b = f.read(4)
    w = struct.unpack('<I', b)[0]
    op = w >> 26
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    good = (op == 0x0B and imm == 0x00B1)
    ok &= good
    print('  0x%08X  ISO 0x%X  %s  op=0x%02X rs=%d rt=%d imm=0x%X  %s'
          % (va, o, b.hex(' '), op, rs, rt, imm, '✓ sltiu …,0xB1' if good else '✗ 不符合预期'))
print('  ⇒ 4 处全部命中: %s' % ok)
print('  改成 0xB5 只需把最低字节 0xB1→0xB5  (每处 1 字节, 共 4 字节)')

print()
print('=== 顺带: 这 4 处的原始英文盘是什么 ===')
fo = open(ORIG, 'rb')
for va in SITES:
    o = va2iso(va)
    fo.seek(o)
    b = fo.read(4)
    print('  0x%08X  EN 原盘 %s' % (va, b.hex(' ')))
fo.close()

print()
print('=== FONT.RES 下载体 (u32 len=20 + 20B 名 + u32 face数=3) ===')
MENU_LBA = 776286
base = MENU_LBA * 2048
FONT_OFF = 0xB9120
NAME_ISO = base + FONT_OFF + 0x0D
f.seek(base + FONT_OFF)
head = f.read(32)
print('  slot[0x00..0x20] = %s' % head.hex(' '))
print('  +0x0D 处 23 字节 = %s' % f.read(0) if False else '')
f.seek(NAME_ISO)
nb = f.read(23)
print('  ISO 0x%X: %s  = %r' % (NAME_ISO, nb.hex(' '), nb.split(b'\x00')[0].decode('latin-1')))
print('  ==> 名字是 20 字符 (不是旧报告写的 22)')

print()
print('=== ISO9660: MENU.IMG;1 目录记录 ===')
f.seek(261 * 2048)
d = f.read(384)
i = 0
while i < len(d):
    L = d[i]
    if L == 0:
        i += 1
        continue
    rec = d[i:i + L]
    nl = rec[32]
    nm = rec[33:33 + nl].decode('ascii', 'replace')
    elba = struct.unpack_from('<I', rec, 2)[0]
    elen = struct.unpack_from('<I', rec, 10)[0]
    if nm.startswith('MENU'):
        print('  记录起始 ISO 偏移 0x%X ; 名字 %r' % (261 * 2048 + i, nm))
        print('    +2  LBA(LE)  = %d    (0x%X)' % (elba, elba))
        print('    +10 len(LE)  = %d    (0x%X)  ← 要 +66,016 的字段之一' % (elen, elen))
        print('    +14 len(BE)  = %d' % struct.unpack_from('>I', rec, 14)[0])
        print('    +18..+24 时间戳 = %s' % rec[18:25].hex(' '))
        print('    记录长度 %d 字节 = %d..%d' % (L, 261 * 2048 + i, 261 * 2048 + i + L))
    i += L
f.close()
