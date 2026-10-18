# -*- coding: utf-8 -*-
r"""root_cfg.py -- 轻量基本块 CFG（READ-ONLY）。给函数入口，按顺序扫到 ret/j，
把分支目标也纳入队列，打印每个基本块的指令。用于快速看清「返回 0 之后怎么走」。

用法: python tools/re/toolbelt/root_cfg.py <entryVA> [<endVA>]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cave_dis  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r72', 'SLUS_206.13.elf')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    e = cave_dis.Elf(ELF)
    entry = int(sys.argv[1], 16)
    hard_end = int(sys.argv[2], 16) if len(sys.argv) > 2 else entry + 0x2000
    seen = set()
    q = [entry]
    order = []
    while q:
        b = q.pop(0)
        if b in seen or not (entry <= b < hard_end):
            continue
        seen.add(b)
        order.append(b)
        pc = b
        while pc < hard_end:
            w = e.word(pc)
            ins = cave_dis.dis(w, pc)
            print('%08x  %08x  %s' % (pc, w, ins))
            op = (w >> 26) & 0x3F
            fn = w & 0x3F
            nxt = pc + 4
            if op == 0 and fn in (8, 9):
                print('')
                break
            if op == 2:
                print('')
                break
            if op in (4, 5, 6, 7, 1, 0x14, 0x15, 0x16, 0x17):
                imm = w & 0xFFFF
                simm = imm - 0x10000 if imm & 0x8000 else imm
                tgt = pc + 4 + simm * 4
                if tgt not in seen:
                    q.append(tgt)
            elif op == 3:
                pass
            pc = nxt
    print('blocks: %s' % ' '.join('0x%X' % b for b in order))


if __name__ == '__main__':
    raise SystemExit(main())
