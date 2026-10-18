# -*- coding: utf-8 -*-
r"""find_readres.py — 在 ELF 里找"记录表分配"站点 (nrec*10+0x10 的 __nwa)

为什么要找: FONT.RES 展开态解析 (`RSFontMgr::ReadResourceFile`) 会做
    nrec = fld[4]*fld[5];  __nwa(nrec*10 + 0x10)
(见 docs/FONTRES_STRUCTURE_r83.md §2.5)。找到这个站点后, 顺着它就能看到
**风格块循环的终止条件** —— 那是判断"多出来的 1280 B 会不会被解析"的关键。

x10 的典型代码形状: sll rd,rt,2 ; addu rd,rd,rt ; sll rd,rd,1
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = r'third_party\orig\ps2\slus_out\SLUS_206.13'
FS = 0x4DED00
d = open(ELF, 'rb').read()


def w(va):
    o = (va - 0x100000) + 0x80
    return struct.unpack_from('<I', d, o)[0] if 0 <= o < len(d) else None


def dec(va, x):
    op = x >> 26
    rs = (x >> 21) & 31
    rt = (x >> 16) & 31
    rd = (x >> 11) & 31
    sa = (x >> 6) & 31
    fn = x & 0x3f
    imm = struct.unpack('<h', struct.pack('<H', x & 0xffff))[0]
    if op == 0 and fn == 0:
        return 'sll r%d,r%d,%d' % (rd, rt, sa)
    if op == 0 and fn == 2:
        return 'srl r%d,r%d,%d' % (rd, rt, sa)
    if op == 0 and fn == 0x21:
        return 'addu r%d,r%d,r%d' % (rd, rs, rt)
    if op == 0 and fn == 0x23:
        return 'subu r%d,r%d,r%d' % (rd, rs, rt)
    if op == 0x09:
        return 'addiu r%d,r%d,%d' % (rt, rs, imm)
    if op == 0x18:
        return 'mult r%d,r%d' % (rs, rt)
    if op == 0x1a:
        return 'div r%d,r%d' % (rs, rt)
    if op == 0x03:
        return 'jal %08X' % (((va + 4) & 0xF0000000) | ((x & 0x03FFFFFF) << 2))
    if op == 0x0f:
        return 'lui r%d,0x%04X' % (rt, x & 0xffff)
    if op == 0x0d:
        return 'ori r%d,r%d,0x%04X' % (rt, rs, x & 0xffff)
    if op == 0x23:
        return 'lw r%d,%d(r%d)' % (rt, imm, rs)
    if op == 0x2b:
        return 'sw r%d,%d(r%d)' % (rt, imm, rs)
    if op == 0x0a:
        return 'slti r%d,r%d,%d' % (rt, rs, imm)
    if op == 0x0b:
        return 'sltiu r%d,r%d,%d' % (rt, rs, imm)
    if op == 0x04:
        return 'beq r%d,r%d,%+d' % (rs, rt, imm)
    if op == 0x05:
        return 'bne r%d,r%d,%+d' % (rs, rt, imm)
    if op == 0x02:
        return 'j %08X' % (((va + 4) & 0xF0000000) | ((x & 0x03FFFFFF) << 2))
    if op == 0 and fn == 8:
        return 'jr r%d' % rs
    return 'op=0x%02X fn=0x%02X' % (op, fn)


hits = []
for va in range(0x100000, 0x100000 + FS - 16, 4):
    a, b, c = w(va), w(va + 4), w(va + 8)
    if a is None or b is None or c is None:
        continue
    if not ((a >> 26) == 0 and (a & 0x3f) == 0 and ((a >> 6) & 31) == 2):
        continue
    rd = (a >> 11) & 31
    rt = (a >> 16) & 31
    if not ((b >> 26) == 0 and (b & 0x3f) == 0x21 and ((b >> 11) & 31) == rd
            and ((b >> 21) & 31) == rd and ((b >> 16) & 31) == rt):
        continue
    if not ((c >> 26) == 0 and (c & 0x3f) == 0 and ((c >> 6) & 31) == 1
            and ((c >> 11) & 31) == rd and ((c >> 16) & 31) == rd):
        continue
    hits.append(va)

print('x10 序列命中 %d 处' % len(hits))
for va in hits[:20]:
    print('--- @%08X (rd=r%d) ---' % (va, (w(va) >> 11) & 31))
    for k in range(-3, 12):
        a2 = va + k * 4
        x = w(a2)
        if x is None:
            continue
        print('    %08X  %08X  %-28s%s' % (a2, x, dec(a2, x), ' <<<' if k == 0 else ''))
