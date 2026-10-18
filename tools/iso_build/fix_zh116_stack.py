# -*- coding: utf-8 -*-
r"""fix_zh116_stack.py — 从卡死时的 EE RAM 走栈, 找调用链 (返回地址 → ELF VA)

用法: python tools/iso_build/fix_zh116_stack.py <eeram.bin> [--sp 0x81FC0] [--elf <iso>]
"""
import argparse
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib  # noqa: E402
from fix_zh116_dis import dis1  # noqa: E402

ELF_LBA = 295
ELF_SIZE = 37453732
SEG_OFF = 0x80
SEG_VA = 0x100000


def elf_at(elf, va, n=12):
    out = []
    for i in range(n):
        o = SEG_OFF + (va - SEG_VA) + i * 4
        if o < 0 or o + 4 > len(elf):
            break
        w = struct.unpack_from('<I', elf, o)[0]
        out.append('%08X  %08X  %s' % (va + i * 4, w, dis1(va + i * 4, w)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ram')
    ap.add_argument('--sp', default='0x81FC0')
    ap.add_argument('--lo', default='0x81D00')
    ap.add_argument('--elf', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso'))
    ap.add_argument('--ctx', default=None, help='VA to disassemble (hex)')
    a = ap.parse_args()
    d = open(a.ram, 'rb').read()
    lo = int(a.lo, 0)
    sp = int(a.sp, 0)
    print('=== 栈里像代码地址的字 (0x%05X..0x%05X) ===' % (lo, sp))
    cands = []
    for off in range(lo, sp, 4):
        v = struct.unpack_from('<I', d, off)[0]
        if SEG_VA <= v < SEG_VA + 0x520000:
            cands.append((off, v))
            print('  [%08X] = %08X' % (off, v))
    if a.elf and os.path.isfile(a.elf):
        f = tcslib.Iso(a.elf)
        elf = f.read(ELF_LBA * 2048, ELF_SIZE)
        f.close()
        print('\n=== 每个候选点前后反汇编 (看是不是跟在 jal 后面的返回地址) ===')
        for off, v in cands[:14]:
            print('-- caller near %08X (stack %08X):' % (v, off))
            for ln in elf_at(elf, v - 0x20, 16):
                print('   ' + ln)
    if a.ctx:
        va = int(a.ctx, 0)
        f = tcslib.Iso(a.elf)
        elf = f.read(ELF_LBA * 2048, ELF_SIZE)
        f.close()
        print('\n=== %08X 附近 ===' % va)
        for ln in elf_at(elf, va, 40):
            print('   ' + ln)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
