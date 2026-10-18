# -*- coding: utf-8 -*-
r"""hgA12_vcargs.py — 只读: 打印 14 个 `RSArray<RSFont>::__vc` 调用点的索引实参 (a1)。

产出: work/builds/GR_HUGE/evidence/hgA12_vcargs.txt
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SITES = [0x1FF9D0, 0x1FFA24, 0x20C660, 0x21C01C, 0x21D77C, 0x22ED24, 0x23CE40,
         0x23F33C, 0x2B87EC, 0x2C20A0, 0x2DDD50, 0x2E82F8, 0x2F0424]


def main():
    lines = []
    W = lines.append
    e, f = H.A.load_elf('ZH113b')
    blob = e.b
    for va in SITES:
        s = e.sym_at(va)
        W('=' * 100)
        W('__vc<RSFont> @%08X  in %s+0x%X' % (va, s['name'], va - s['value']))
        for (a, w, t) in H.dis_range(blob, va - 10 * 4, 16, H.VA2FILE):
            mark = ' <<<' if a == va else '    '
            W('   %08X  %08X  %-30s%s' % (a, w if w is not None else 0, t, mark))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA12_vcargs.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA12_vcargs.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
