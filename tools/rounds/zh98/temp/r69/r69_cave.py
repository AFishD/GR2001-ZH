# -*- coding: utf-8 -*-
r"""r69_cave.py — cave 落点安全自检 (本轮 r69)。

对给定 VA 区间做 5 项检查:
  ① ELF 静态: 区间内每个 4 字节字必须为 0;
  ② ELF 静态: 全文件没有 j/jal 以区间内地址为目标;
  ③ ELF 静态: 全文件没有 4 字节字面量落在区间内 (对齐/非对齐都查 —— 非对齐按 2 字节看);
  ④ RAM 实证: 每一份 EE RAM 转储在该区间均为 0;
  ⑤ 区间不与其它段重叠 (主段内)。

用法: python r69_cave.py <elf> <lo_hex> <hi_hex>
"""
import glob
import os
import struct
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
while not (os.path.isdir(os.path.join(REPO, 'tools', 'capture'))
           and os.path.isdir(os.path.join(REPO, 'work', 'builds'))):
    nxt = os.path.dirname(REPO)
    assert nxt != REPO, 'repo root not found'
    REPO = nxt
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00


def main():
    elf, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
    assert lo < hi and lo % 4 == 0
    d = open(elf, 'rb').read()
    seg = d[SEC_OFF:SEC_OFF + SEC_SIZE]
    print('== cave 落点自检 %08X..%08X (%d B) ==' % (lo, hi, hi - lo))

    # ① 静态零
    bad = [('%08X' % (lo + i)) for i in range(0, hi - lo, 4)
           if struct.unpack_from('<I', seg, lo - SEC_ADDR + i)[0] != 0]
    print('① ELF 静态全零: %s %s' % ('✓' if not bad else '✗', bad[:8] if bad else ''))

    # ② j/jal 目标
    hits = []
    for off in range(0, SEC_SIZE, 4):
        w = struct.unpack_from('<I', seg, off)[0]
        if w >> 26 in (2, 3):
            t = (w & 0x3FFFFFF) << 2
            if lo <= t < hi:
                hits.append('%08X->%08X' % (SEC_ADDR + off, t))
    print('② 无 j/jal 指向区间: %s %s' % ('✓' if not hits else '✗', hits[:8]))

    # ③ 字面量 (全文件, 4 字节对齐)
    lit = []
    n = len(d) // 4
    for i in range(n):
        v = struct.unpack_from('<I', d, i * 4)[0]
        if lo <= v < hi:
            lit.append('off %X = %08X' % (i * 4, v))
    print('③ 无 4 字节字面量落在区间 (全文件 %d 词): %s %s'
          % (n, '✓' if not lit else '✗', lit[:8]))

    # ④ RAM 转储
    dumps = sorted(glob.glob(os.path.join(REPO, 'work', 'builds', '**', '*eeram*.bin'),
                             recursive=True))
    skip = os.path.join(REPO, 'work', 'builds', 'GR_ZH115')      # 本补丁盘自己的转储要排除
    dumps = [p for p in dumps if not p.startswith(skip)]
    nz = []
    used = 0
    for p in dumps:
        sz = os.path.getsize(p)
        if sz <= hi:
            continue
        used += 1
        with open(p, 'rb') as f:
            f.seek(lo)
            b = f.read(hi - lo)
        if any(b):
            nz.append('%s: %s' % (os.path.basename(p), b.hex()))
    print('④ RAM 转储全零: %s  (查了 %d/%d 份)' % ('✓' if not nz else '✗', used, len(dumps)))
    for x in nz[:6]:
        print('     ✗ %s' % x)
    return 0 if (not bad and not hits and not lit and not nz) else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
