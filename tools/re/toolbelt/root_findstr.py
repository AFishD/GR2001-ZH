# -*- coding: utf-8 -*-
r"""root_findstr.py -- 在 ELF 里搜 ASCII 子串（READ-ONLY），给 VA。

用法: python tools/re/toolbelt/root_findstr.py <substr> [<substr> ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cave_dis  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r72', 'SLUS_206.13.elf')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    e = cave_dis.Elf(ELF)
    d = e.d
    for s in sys.argv[1:]:
        pat = s.encode('latin-1')
        n = 0
        pos = 0
        while True:
            i = d.find(pat, pos)
            if i < 0:
                break
            # map file offset -> VA
            va = None
            for (v, o, fs) in e.segs:
                if o <= i < o + fs:
                    va = v + (i - o)
                    break
            print('%-40s file 0x%08X  VA %s' % (s, i, ('0x%08X' % va) if va else '(not in PT_LOAD)'))
            n += 1
            pos = i + 1
        if n == 0:
            print('%-40s NOT FOUND' % s)


main()
