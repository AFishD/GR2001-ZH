# -*- coding: utf-8 -*-
r"""lay_classify.py —— 【GR_LAYOUT】把"几何常量站点"逐条分类：落在汉化改写区(M) 还是原盘原码(O)。

用法: python lay_classify.py <orig.elf> <k2.elf> [-o out.txt]
输出: 每个常量 K 一张表：VA / 寄存器 / M|O / R5900 指令 / 与汉化图集布局的关系初判
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lay_dis import Elf, dis_r5900  # noqa: E402

KS = [3, 12, 16, 18, 19, 62, 63, 64, 94, 104, 224, 512, 640, 644, 1024, 1280,
      1736, 1872, 2344, 2350, 2368, 2432, 329744]

# 汉化"图集/字库布局"核心区（人工登记，由 orig-vs-K2 逐字 diff 得出）
HOT = [
    (0x416ED0, 0x416F40, 'decode cave（汉化新增）'),
    (0x416F40, 0x417038, 'CharWidth cave（汉化新增，含 ×94 与 +0xE0）'),
    (0x417050, 0x417140, 'GetGlyphUV cave（汉化新增，含 NCOL/SKIP/Y0/V1）'),
    (0x417150, 0x4171A8, 'StringWidth cave（汉化新增，含 GATE#2）'),
    (0x4171A8, 0x4171C8, 'StringWidth cave 尾'),
    (0x417200, 0x417220, 'DrawString 改写片段'),
    (0x417500, 0x4175A0, 'gate#3 cave'),
    (0x4175A8, 0x417600, 'glyph count cave'),
    (0x417600, 0x417720, '容量钳位 cave'),
    (0x565670, 0x565740, 'Measure 尾 cave（含 GATE#4）'),
    (0x565900, 0x565AC0, 'DrawString 拦截器'),
]


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
    oh, kh = argv[1], argv[2]
    o = Elf(oh)
    k = Elf(kh)

    # 1) 汉化改写集合（逐字 diff）
    n = min(len(o.d), len(k.d))
    changed = set()
    for off in range(0, n - 3, 4):
        if o.d[off:off + 4] != k.d[off:off + 4]:
            for (v, so, ss, _fl) in k.segs:
                if so <= off < so + ss:
                    changed.add(v + (off - so))
                    break
    out.write('# A(原盘) = %s\n# B(K2)   = %s\n' % (oh, kh))
    out.write('# 汉化改写字数 = %d\n' % len(changed))
    out.write('# 汉化改写区的 VA 区间: ')
    sp = sorted(changed)
    runs = []
    for v in sp:
        if runs and v == runs[-1][1] + 4:
            runs[-1][1] = v
        else:
            runs.append([v, v])
    out.write(', '.join('0x%X..0x%X' % (a, b) for (a, b) in runs) + '\n')

    va0, _so, fsz = k.text()
    for K in KS:
        hits = []
        for va in range(va0, va0 + fsz - 4, 4):
            w = k.word(va)
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            if op == 0x09 and rs == 0:          # addiu rt,zero,K
                imm = w & 0xFFFF
                simm = imm - 0x10000 if imm & 0x8000 else imm
                if simm == K:
                    hits.append((va, w))
        out.write('\n## K = %-6d  共 %d 处\n' % (K, len(hits)))
        for (va, w) in hits:
            tag = 'M' if va in changed else 'O'
            why = ''
            for (lo, hi, name) in HOT:
                if lo <= va < hi:
                    why = name
                    break
            out.write('   %08X  %s  %08X  %-46s %s\n'
                      % (va, tag, w, dis_r5900(w, va), why))
    if outpath:
        out.close()
        print('[out] %s' % outpath)


if __name__ == '__main__':
    main()
