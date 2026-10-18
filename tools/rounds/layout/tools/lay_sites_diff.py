# -*- coding: utf-8 -*-
r"""lay_sites_diff.py —— 【GR_LAYOUT】逐站点对照：原盘 vs K2 同一 VA 附近 ±N 条指令。

用法: python lay_sites_diff.py <orig.elf> <k2.elf> <VA> [<VA> ...] [--n 6] [-o out]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lay_dis import Elf, dis_r5900  # noqa: E402


def main():
    argv = sys.argv[:]
    outpath = None
    n = 6
    if '-o' in argv:
        i = argv.index('-o')
        outpath = argv[i + 1]
        del argv[i:i + 2]
    if '--n' in argv:
        i = argv.index('--n')
        n = int(argv[i + 1])
        del argv[i:i + 2]
    out = open(outpath, 'w', encoding='utf-8', newline='\n') if outpath else sys.stdout
    if not outpath:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    o, k = Elf(argv[1]), Elf(argv[2])
    out.write('# 原盘 = %s\n# K2   = %s\n' % (os.path.abspath(argv[1]), os.path.abspath(argv[2])))
    for s in argv[3:]:
        va = int(s, 16)
        out.write('\n' + '=' * 104 + '\n# VA 0x%08X  ±%d 条\n' % (va, n))
        for d in range(-4 * n, 4 * (n + 1), 4):
            v = va + d
            try:
                wo, wk = o.word(v), k.word(v)
            except SystemExit:
                continue
            tag = '★' if v == va else ' '
            same = '  ' if wo == wk else '≠≠'
            out.write('  %s%s %08X\n' % (tag, same, v))
            out.write('        orig %08X  %s\n' % (wo, dis_r5900(wo, v)))
            if wo != wk:
                out.write('        K2   %08X  %s\n' % (wk, dis_r5900(wk, v)))
    if outpath:
        out.close()
        print('[out] %s' % outpath)


if __name__ == '__main__':
    main()
