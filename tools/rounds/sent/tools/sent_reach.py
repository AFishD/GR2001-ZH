# -*- coding: utf-8 -*-
r"""sent_reach.py —— 静态可达性探针：谁跳进/调进某个 VA 区间？

用法：python sent_reach.py <elf|--iso ISO> <loVA> <hiVA> [--tag NAME]
输出：所有把控制流送进 [lo,hi) 的 j/jal/branch 站点（含其自身的函数归属线索）。
只读。
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

ISO_OF_VA = 0x6C780
BRANCH_OPS = (0x01, 0x04, 0x05, 0x06, 0x07, 0x14, 0x15, 0x16, 0x17)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    src = sys.argv[1]
    lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
    tag = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(src)

    if src.startswith('--iso='):
        iso = src[6:]
        f = open(iso, 'rb')
        hint = 0x100000 - ISO_OF_VA
        base = None
        for off in range(hint, hint - 0x400, -1):
            f.seek(off)
            if f.read(4) == b'\x7fELF':
                base = off
                break
        import struct
        f.seek(base + 0x34)
        _t, poff, pva = struct.unpack('<3I', f.read(12))
        delta = base + poff - pva

        def word(va):
            f.seek(delta + va)
            return struct.unpack('<I', f.read(4))[0]
        va0, fsz = pva, 0x4DED00
    else:
        elf = CD.Elf(src)
        va0, _o, fsz = elf.text()
        word = elf.word

    hits = []
    for va in range(va0, va0 + fsz - 4, 4):
        w = word(va)
        op = (w >> 26) & 0x3F
        tgt = None
        if op in (2, 3):
            tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
        elif op in BRANCH_OPS:
            simm = w & 0xFFFF
            if simm & 0x8000:
                simm -= 0x10000
            tgt = va + 4 + simm * 4
        if tgt is not None and lo <= tgt < hi:
            hits.append((va, w, tgt, op))

    print('# 目标区间 [0x%08X, 0x%08X)  —— %s' % (lo, hi, tag))
    print('# 进入该区间的控制流站点 = %d 个' % len(hits))
    for (va, w, tgt, op) in hits:
        print('  0x%08X  op=0x%02X → 0x%08X   %s' % (va, op, tgt, CD.dis(w, va)))


if __name__ == '__main__':
    main()
