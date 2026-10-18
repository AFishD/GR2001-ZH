# -*- coding: utf-8 -*-
r"""lay_reach.py —— 【GR_LAYOUT】可达性/改写区一致性检查（只读）。

用法: python lay_reach.py <elf> <lo> <hi> [...]
  · 打印所有 j/jal 与该区间相关的站点
  · 打印所有 **分支**(beq/bne/blez/bgtz/bltz/bgez/bc1f/bc1t) 目标落在该区间的站点
  · 同时列出该区间内每条指令的"是否被 j/jal/分支 指向"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lay_dis import Elf, dis_r5900  # noqa: E402

BRANCH_OPS = {0x01, 0x04, 0x05, 0x06, 0x07, 0x11, 0x14, 0x15, 0x16, 0x17}


def branch_target(w, pc):
    op = (w >> 26) & 0x3F
    if op in (0x04, 0x05, 0x06, 0x07, 0x01):
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        return pc + 4 + (simm << 2)
    if op == 0x11 and ((w >> 21) & 0x1F) == 0x08:
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        return pc + 4 + (simm << 2)
    if op in (0x14, 0x15, 0x16, 0x17):
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        return pc + 4 + (simm << 2)
    return None


def main():
    argv = sys.argv[:]
    outpath = None
    if '-o' in argv:
        i = argv.index('-o')
        outpath = argv[i + 1]
        del argv[i:i + 2]
    out = open(outpath, 'w', encoding='utf-8', newline='\n') if outpath else sys.stdout
    if not outpath:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = Elf(argv[1])
    spans = [(int(argv[i], 16), int(argv[i + 1], 16)) for i in range(2, len(argv) - 1, 2)]
    va0, _o, fsz = elf.text()
    out.write('# %s\n' % os.path.abspath(argv[1]))
    for (lo, hi) in spans:
        out.write('\n' + '=' * 100 + '\n# 区间 [0x%08X, 0x%08X)\n' % (lo, hi))
        # 1) 区间内指令的入边
        inbound = {}
        for va in range(va0, va0 + fsz - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            tgt = None
            if op in (2, 3):
                tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                kind = 'j' if op == 2 else 'jal'
            else:
                tgt = branch_target(w, va)
                kind = 'br'
            if tgt is not None and lo <= tgt < hi:
                inbound.setdefault(tgt, []).append((va, kind, w))
        out.write('# ── 区间内的"入口点"(有外部 j/jal/分支 指向的地址) ──\n')
        if not inbound:
            out.write('   (无)\n')
        for tgt in sorted(inbound):
            for (va, kind, w) in inbound[tgt]:
                out.write('   → 0x%08X  ← %s 0x%08X  %s\n' % (tgt, kind, va, dis_r5900(w, va)))
        # 2) 区间逐条 + 是否为入口 / 是否直接后继
        out.write('# ── 区间逐条（★ = 有外部入口；↓ = 上一条的回退目标；行尾标 M/O = 相对原盘是否被改）──\n')
        for va in range(lo, hi, 4):
            w = elf.word(va)
            mark = '★' if va in inbound else ' '
            out.write('  %s %08X  %08X  %s\n' % (mark, va, w, dis_r5900(w, va)))
    if outpath:
        out.close()
        print('[out] %s' % outpath)


if __name__ == '__main__':
    main()
