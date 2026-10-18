# -*- coding: utf-8 -*-
r"""lay_map.py —— 列出 ELF 里所有 j/jal，按目标区间过滤（只读）。

用法: python lay_map.py <elf> <lo> <hi>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lay_dis import Elf, dis_r5900  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = None
    argv = sys.argv[:]
    if '-o' in argv:
        i = argv.index('-o')
        out = argv[i + 1]
        del argv[i:i + 2]
    if out:
        sys.stdout = open(out, 'w', encoding='utf-8', newline='\n')
    elf = Elf(argv[1])
    lo, hi = int(argv[2], 16), int(argv[3], 16)
    va0, _o, fsz = elf.text()
    print('# j/jal 目标落在 [0x%08X, 0x%08X) 的站点' % (lo, hi))
    n = 0
    for va in range(va0, va0 + fsz - 4, 4):
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        if op in (2, 3):
            tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            if lo <= tgt < hi:
                # 打印跳转点前后各 2 条，便于看上下文
                for d in (-8, -4, 0, 4):
                    ww = elf.word(va + d)
                    mark = '>>' if d == 0 else '  '
                    print('  %s %08x  %08x  %s' % (mark, va + d, ww, dis_r5900(ww, va + d)))
                print('  ' + '-' * 60)
                n += 1
    print('# 共 %d 处' % n)


if __name__ == '__main__':
    main()
