# -*- coding: utf-8 -*-
r"""p11_icon_texture.py — round42: 找出 RSFontMgr 图标 model 用的纹理文件名, 并从 ISO 里把它抠出来

ELF 证据 (RSFontMgr::ReadResourceFile @0x219380 尾部):
    002197CC  lw $t9, 76($s5)             ; 第二个 UISpriteModel (图标用)
    002197DC  addiu $a1, $zero, 2         ; 容量 = 2 quad
    002197E8  jal GetTexture(RSFilename&) ; a1 = this+28 (字体名) → SetTexture(this+40)
    00219800  lui $v0, 0x0058
    0021980C  addiu $a1, $v0, -31152      ; a1 = *(0x578650) —— 一个硬编码字符串地址
    00219828  jal SetTexture(this+76)     ; ★ 图标 model 用**这个文件名**的纹理
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
data = open(ELF, 'rb').read()
SEC_OFF, SEC_ADDR = 0x80, 0x00100000


def at(va, n=64):
    return data[SEC_OFF + va - SEC_ADDR: SEC_OFF + va - SEC_ADDR + n]


va = 0x578650
print('0x%08X 处的内容:' % va)
print('  hex : %s' % at(va, 48).hex(' '))
print('  文本: %r' % at(va, 48).split(b'\0')[0])
print('  → 字符串指针 *(0x578650) = 0x%08X'
      % struct.unpack_from('<I', data, SEC_OFF + va - SEC_ADDR)[0])
p = struct.unpack_from('<I', data, SEC_OFF + va - SEC_ADDR)[0]
print('  → 该地址处的字符串: %r' % at(p, 64).split(b'\0')[0])

print()
print('附近 0x578600..0x578700 的 C 字符串:')
i = 0x578600
while i < 0x578700:
    s = at(i, 64).split(b'\0')[0]
    if len(s) >= 4 and all(32 <= c < 127 for c in s):
        print('  0x%08X  %r' % (i, s))
        i += len(s) + 1
    else:
        i += 1
