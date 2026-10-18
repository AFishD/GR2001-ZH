# -*- coding: utf-8 -*-
r"""hgA4_symq.py — 只读: 打印符号表里 VA 落在若干区间内的全部符号，用于给调用点归名。

产出: work/builds/GR_HUGE/evidence/hgA4_symq.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

RANGES = [
    (0x219300, 0x21B100),      # RSFontMgr / RSFont 邻域
    (0x3A1700, 0x3A1900),      # GetFont / Get
    (0x578600, 0x578700),      # ctor 里引用的字符串
    (0x541600, 0x542100),      # RSString 相关
    (0x51B000, 0x51B100),      # 0x51B040
    (0x516A00, 0x516B00),      # 0x516A20
]
EXTRA = [0x21A750, 0x219920, 0x21A770, 0x21A9A0, 0x541640, 0x541CA0, 0x51B040, 0x516A20,
         0x53D4F0, 0x53FCA0, 0x53FE40, 0x54D0F0, 0x4D1290, 0x102D40, 0x14A020, 0x103360,
         0x118EE0, 0x53E2B0, 0x53FD50, 0x406F28, 0x40BFC8, 0x542020]


def main():
    lines = []
    W = lines.append
    e, f = H.A.load_elf('ZH113b')
    W('ELF syms=%d' % len(e.syms))
    for (a, b) in RANGES:
        W('=' * 100)
        W('--- 区间 0x%X..0x%X ---' % (a, b))
        for s in sorted([q for q in e.syms if a <= q['value'] < b], key=lambda x: x['value']):
            W('  0x%08X size=%-6d %-9s %s' % (s['value'], s['size'], s['typname'], s['name']))
    W('=' * 100)
    W('--- 指定地址最近符号 ---')
    for va in EXTRA:
        s = e.sym_at(va)
        W('  0x%08X -> %s' % (va, ('0x%08X +0x%X  %s (size=%d)' %
                                   (s['value'], va - s['value'], s['name'], s['size']))
                              if s else '?'))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA4_symq.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA4_symq.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
