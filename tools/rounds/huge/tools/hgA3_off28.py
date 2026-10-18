# -*- coding: utf-8 -*-
r"""hgA3_off28.py — 只读: 全 ELF 扫描「对某对象 +0x28 (=40) 的读写」与「&obj[0x28] 的取址」，
并用符号表把命中的函数归名 —— 目的: 找出 RSFont 的 face 指针 (+0x28) 由谁写入。

口径:
  (a) `lw/sw reg, 40(base)`   ⇒ 直接读写该字段
  (b) `addiu dst, base, 40`   ⇒ 取 &obj[0x28]（通常立刻作为参数交给 reader/copy）
  (c) `lb/lbu/lh/lhu/sb/sh reg, 40(base)`

产出: work/builds/GR_HUGE/evidence/hgA3_off28.txt
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

R = H.A.R
TARGET = 40      # 0x28


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        blob = e.b
        W('=' * 110)
        W('%s  ELF len=%d' % (tag, len(blob)))
        hits_a, hits_b = [], []
        # 线性扫 text 段: PH type=1 flags 可执行 (R5900: PH flags & 0x1 = X)
        for p in e.phdrs:
            if p['type'] != 1:
                continue
            va0, va1 = p['vaddr'], p['vaddr'] + p['filesz']
            for a in range(va0, va1, 4):
                o = a - H.VA2FILE
                if o < 0 or o + 4 > len(blob):
                    continue
                w = struct.unpack_from('<I', blob, o)[0]
                op = w >> 26
                imm = w & 0xFFFF
                simm = imm - 0x10000 if imm & 0x8000 else imm
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                if simm == TARGET and op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x27,
                                             0x28, 0x29, 0x2B, 0x1E, 0x1F, 0x37, 0x3F):
                    hits_a.append((a, w, H.A.dis1(w, a)))
                if simm == TARGET and op == 0x09:      # addiu
                    hits_b.append((a, w, H.A.dis1(w, a), rs, rt))
        W('--- (a) 读/写 40(base)  命中 %d ---' % len(hits_a))
        for (a, w, t) in hits_a:
            s = e.sym_at(a)
            W('  %08X  %08X  %-34s  %s' % (a, w, t,
                                           ('%s+0x%X' % (s['name'], a - s['value'])) if s else '?'))
        W('')
        W('--- (b) addiu dst, base, 40  (&obj[0x28] 取址)  命中 %d ---' % len(hits_b))
        for (a, w, t, rs, rt) in hits_b:
            s = e.sym_at(a)
            W('  %08X  %08X  %-34s  %s' % (a, w, t,
                                           ('%s+0x%X' % (s['name'], a - s['value'])) if s else '?'))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA3_off28.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA3_off28.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
