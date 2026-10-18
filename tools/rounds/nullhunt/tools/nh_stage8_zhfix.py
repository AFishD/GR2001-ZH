# -*- coding: utf-8 -*-
r"""nh_stage8_zhfix.py — ZH113b 与 ZH113b_fix 的精确差异 + VA 归属 (只读)"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402
import nh_stage3_elf as S3   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    a = N.Iso(N.ISO['ZH113b'])
    b = N.Iso(N.ISO['ZH113b_fix'])
    f = [v for k, v in a.files().items() if 'SLUS_206.13' in k][0]
    base = f['lba'] * N.SEC
    e_en, _ = S3.load_elf('EN_ORIG')
    e_a, _ = S3.load_elf('ZH113b')
    e_b, _ = S3.load_elf('ZH113b_fix')

    buf = io.StringIO()
    # 逐字节精确扫描 ELF 区
    runs = []
    A, B = e_a.b, e_b.b
    n = len(A)
    i = 0
    while i < n:
        if A[i] == B[i]:
            i += 1
            continue
        j = i
        while j < n and A[j] != B[j]:
            j += 1
        runs.append((i, j))
        i = j
    buf.write('ZH113b -> ZH113b_fix : ELF 精确差异 run = %d, 字节 = %s\n'
              % (len(runs), N.fmt(sum(e - s for s, e in runs))))
    for (s, e) in runs:
        va, _ = e_en.off2va(s)
        sym = e_en.sym_at(va) if va else None
        buf.write('\n  ELF FILE 0x%06X..0x%06X (len=%d)  VA 0x%X..0x%X  %s +0x%X\n'
                  % (s, e, e - s, va, (e_en.off2va(e - 1)[0] or 0) + 1,
                     sym['name'] if sym else '?', (va - sym['value']) if sym else 0))
        buf.write('    ISO 字节 0x%X..0x%X\n' % (base + s, base + e))
        for o in range(s & ~3, (e + 3) & ~3, 4):
            ova, _ = e_en.off2va(o)
            w0 = struct.unpack_from('<I', A, o)[0]
            w1 = struct.unpack_from('<I', B, o)[0]
            mark = '  ' if w0 == w1 else ' *'
            buf.write('%s VA 0x%08X  b   %08X %-34s | fix %08X %-34s\n'
                      % (mark, ova, w0, E.mips_dis1(w0, ova), w1, E.mips_dis1(w1, ova)))
        buf.write('    原始 16B 切片 b  : %s\n' % A[s:s + 16].hex(' '))
        buf.write('    原始 16B 切片 fix: %s\n' % B[s:s + 16].hex(' '))
    # 上下文
    for (s, e) in runs:
        va, _ = e_en.off2va(s)
        sym = e_en.sym_at(va)
        buf.write('\n  --- 上下文 (±12 条指令, 以 fix 版为准) ---\n')
        for k in range(-12, 16):
            o = (s & ~3) + k * 4
            ova, _ = e_en.off2va(o)
            if ova is None:
                continue
            w = struct.unpack_from('<I', B, o)[0]
            mark = ' *' if (s & ~3) <= o < e else '  '
            buf.write('%s 0x%08X  %08X  %s\n' % (mark, ova, w, E.mips_dis1(w, ova)))
        break
    # 整个 ISO 是否还有别处不同
    buf.write('\n== ISO 全盘其它区域差异 ==\n')
    others = 0
    for lbl, off, ln in (('LBA0..256', 0, 256 * N.SEC),
                         ('LBA 256..295', 256 * N.SEC, 40 * N.SEC),
                         ('GR.IMG 头部 0x10000', 19175 * N.SEC, 0x10000),
                         ('MENU.IMG 头部 0x10000', 776286 * N.SEC, 0x10000)):
        xa = a.rd(off, ln)
        xb = b.rd(off, ln)
        d = sum(1 for p, q in zip(xa, xb) if p != q)
        others += d
        buf.write('  %-24s 不同 %d / %d\n' % (lbl, d, ln))
    buf.write('  上述抽样合计不同 = %d ⇒ %s\n'
              % (others, '两盘差异只在 ELF 0x%X..0x%X' % (runs[0][0], runs[0][1])
                 if others == 0 else '还有别处差异, 需全盘扫'))
    a.close()
    b.close()
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage8_zh113b_vs_fix.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
