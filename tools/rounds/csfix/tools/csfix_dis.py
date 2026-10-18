# -*- coding: utf-8 -*-
r"""csfix_dis.py —— 对**从 BlockDump 取回的 K2 ELF**做定向反汇编（只读）。

用法：
  python csfix_dis.py <elf> <VA_lo> <VA_hi> [...]   # 每两个参数一个区间
  python csfix_dis.py <elf> --callers <VA>          # 打印所有 jal/j 到该 VA 的站点
  python csfix_dis.py <elf> --word <VA> [...]       # 逐 VA 打印字 + 反汇编
"""
import os
import struct
import sys
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    args = sys.argv[2:]
    if args and args[0] == '--callers':
        va0, _o, fsz = elf.text()
        want = [int(x, 16) for x in args[1:]]
        for va in range(va0, va0 + fsz - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            if op in (2, 3):
                tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if tgt in want:
                    print('  0x%08X → 0x%08X  %s' % (va, tgt, CD.dis(w, va)))
        return
    if args and args[0] == '--word':
        for s in args[1:]:
            va = int(s, 16)
            w = elf.word(va)
            print('  VA 0x%08X = 0x%08X  %s' % (va, w, CD.dis(w, va)))
        return
    for i in range(0, len(args) - 1, 2):
        lo, hi = int(args[i], 16), int(args[i + 1], 16)
        print('=' * 90)
        print('# [0x%08X, 0x%08X)' % (lo, hi))
        for va in range(lo, hi, 4):
            w = elf.word(va)
            print('  %08x  %08x  %-46s ; %s'
                  % (va, w, CD.dis(w, va), struct.pack('<I', w).hex()))


if __name__ == '__main__':
    main()
