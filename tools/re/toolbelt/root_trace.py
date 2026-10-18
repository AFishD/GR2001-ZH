# -*- coding: utf-8 -*-
r"""root_trace.py -- 轻量控制流跟踪（READ-ONLY）：给一个 VA，递归跟随分支/jal，
打印函数树与关键常量比较。用于 round85 根因定位。

用法: python tools/re/toolbelt/root_trace.py fn <VA> [depth]      # 以 VA 为入口的线性反汇编+分支目标
      python tools/re/toolbelt/root_trace.py back <VA> [n]        # 从 VA 往前找函数序言 (addiu $sp,$sp,-N)
      python tools/re/toolbelt/root_trace.py xref <VA>            # 谁引用这个 VA（jal/j/branch/数据字）
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
    va0, off, fs = e.text()
    mode = sys.argv[1]
    if mode == 'back':
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 64
        for k in range(1, n + 1):
            w = e.word(va - 4 * k)
            ins = cave_dis.dis(w, va - 4 * k)
            if ins.startswith('addiu $sp, $sp, -') or ins.startswith('addiu $sp,$sp,-'):
                print('  函数序言候选 @0x%08X : %s' % (va - 4 * k, ins))
                for j in range(0, k + 6):
                    p = va - 4 * k + 4 * j
                    print('    %08x  %08x  %s' % (p, e.word(p), cave_dis.dis(e.word(p), p)))
                break
        else:
            print('  前 %d 条里没找到序言' % n)
    elif mode == 'xref':
        t = int(sys.argv[2], 16)
        n = 0
        for va in range(va0, va0 + fs - 4, 4):
            w = e.word(va)
            op = (w >> 26) & 0x3F
            if op in (2, 3):
                tt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if tt == t:
                    print('  %s @0x%08X' % ('jal' if op == 3 else 'j  ', va))
                    n += 1
            elif op in (4, 5, 6, 7, 1, 0x14, 0x15, 0x16, 0x17):
                imm = w & 0xFFFF
                simm = imm - 0x10000 if imm & 0x8000 else imm
                if va + 4 + simm * 4 == t:
                    print('  branch @0x%08X  %s' % (va, cave_dis.dis(w, va)))
                    n += 1
            if w == t:
                print('  data-word @0x%08X' % va)
                n += 1
        print('  total %d' % n)
    elif mode == 'fn':
        va = int(sys.argv[2], 16)
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        seen = set()
        frontier = [(va, 0, 'entry')]
        while frontier:
            cur, d, why = frontier.pop(0)
            if cur in seen or d > depth:
                continue
            seen.add(cur)
            print('--- 0x%08X (depth %d, %s) ---' % (cur, d, why))
            # 从 cur 线性走，遇 jr $ra 或 j 跳出则停
            pc = cur
            while pc < va0 + fs - 8:
                w = e.word(pc)
                ins = cave_dis.dis(w, pc)
                print('  %08x  %08x  %s' % (pc, w, ins))
                op = (w >> 26) & 0x3F
                fn = w & 0x3F
                if op == 0 and fn == 8:      # jr
                    break
                if op == 2:                  # j
                    print('   -> j to 0x%08X' % (((w & 0x03FFFFFF) << 2) | (pc & 0xF0000000)))
                    break
                if op == 3:
                    t = ((w & 0x03FFFFFF) << 2) | (pc & 0xF0000000)
                    frontier.append((t, d + 1, 'jal from 0x%08X' % pc))
                nextpc = pc + 4
                # 分支: 记录目标
                if op in (4, 5, 6, 7, 1, 0x14, 0x15, 0x16, 0x17):
                    imm = w & 0xFFFF
                    simm = imm - 0x10000 if imm & 0x8000 else imm
                    tgt = pc + 4 + simm * 4
                    print('   -> branch to 0x%08X' % tgt)
                pc = nextpc
            print()
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
