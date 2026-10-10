# -*- coding: utf-8 -*-
r"""cop1.py — EE COP1 (浮点) 指令解码 (会话工具): python cop1.py <elf> <hexVA> <字节数>
只解 COP1 S/W 格式 (op=0x11), 其余交给 dis_ee.py。
"""
import os
import struct
import sys

SEC_OFF, SEC_ADDR = 0x80, 0x00100000
FR = ['$f%d' % i for i in range(32)]
FN = {0: 'add', 1: 'sub', 2: 'mul', 3: 'div', 4: 'sqrt', 5: 'abs', 6: 'mov', 7: 'neg',
      0x20: 'cvt.s', 0x21: 'cvt.w', 0x24: 'cvt.w(trunc)', 0x22: 'cvt.w(ceil)',
      0x23: 'cvt.w(floor)', 0x1C: 'madd', 0x1D: 'msub', 0x1E: 'mula', 0x1F: 'mula'}
FMT = {0x10: 'S', 0x14: 'W', 0x11: 'D'}


def main():
    elf, va, ln = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 0)
    d = open(elf, 'rb').read()
    for a in range(0, ln, 4):
        w = struct.unpack_from('<I', d, SEC_OFF + (va - SEC_ADDR) + a)[0]
        if (w >> 26) != 0x11:
            continue
        fmt = (w >> 21) & 0x1F
        ft, fs, fd, fn = (w >> 16) & 0x1F, (w >> 11) & 0x1F, (w >> 6) & 0x1F, w & 0x3F
        if fmt == 0x04 and fn == 0:
            s = 'mtc1 %s, %s' % (['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3','$t0','$t1',
                                  '$t2','$t3','$t4','$t5','$t6','$t7','$s0','$s1','$s2','$s3',
                                  '$s4','$s5','$s6','$s7','$t8','$t9','$k0','$k1','$gp','$sp',
                                  '$fp','$ra'][ft], FR[fs])
        elif fmt == 0x00 and fn == 0:
            s = 'mfc1 %s, %s' % (FR[fs], ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                                           '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                                           '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                                           '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra'][rt]
                                   if False else FR[fs])
        elif fmt in (0x10, 0x14, 0x11):
            name = FN.get(fn, 'fn%02X' % fn)
            s = '%s.%s %s, %s, %s' % (name, FMT[fmt], FR[fd], FR[fs], FR[ft])
        else:
            s = '.word %08X' % w
        print('%08X  %s' % (va + a, s))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
