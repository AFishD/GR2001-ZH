# -*- coding: utf-8 -*-
r"""cvar_elf.py — P1: 列出 SLUS_206.13 内的全部字节差异 (VA / ISO / 改前改后)

用法: python cvar_elf.py --a <EN.iso> --b <ZH.iso> --runs <json> [--out <txt>] [--group-gap N]

假设由仓库既有工具确定: ELF ISO 基址 0x93880, VA 基址 0x100000
  ⇒ VA = ISO - 0x93880 + 0x100000
另给出 ELF 程序头 (PT_LOAD) 表, 用于判定某 VA 属于哪个段。
"""
import argparse
import json
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
ELF_LBA = 295
ELF_ISO_BASE = ELF_LBA * SEC          # 0x93800  (ELF 文件起点)
ELF_VA_BASE_KNOWN = 0x100000
ELF_ISO_VA_ANCHOR = 0x93880           # 该 ISO 偏移 == VA 0x100000 (既有工具口径)


def va_of_iso(o):
    return o - ELF_ISO_VA_ANCHOR + ELF_VA_BASE_KNOWN


def iso_of_va(v):
    return v - ELF_VA_BASE_KNOWN + ELF_ISO_VA_ANCHOR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--runs', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--group-gap', type=int, default=64)
    x = ap.parse_args()
    A = open(x.a, 'rb').read()
    B = open(x.b, 'rb').read()
    D = json.load(open(x.runs, encoding='utf-8'))

    eh = struct.unpack_from('<4s5B7x2H5I6H3I2H', A, ELF_ISO_BASE)
    print('ELF magic=%r class=%d endian=%d  e_entry=0x%X phoff=0x%X shoff=0x%X'
          % (eh[0], eh[1], eh[2], eh[11], eh[12], eh[13]))
    phoff = eh[12]
    phnum = eh[15]
    print('程序头 %d 个 @文件 0x%X (ISO 0x%X)' % (phnum, phoff, ELF_ISO_BASE + phoff))
    segments = []
    for i in range(phnum):
        p = struct.unpack_from('<8I', A, ELF_ISO_BASE + phoff + 32 * i)
        typ, off, vaddr, paddr, filesz, memsz, flags, align = p
        if typ == 1:
            segments.append((vaddr, vaddr + memsz, off, filesz, memsz, flags))
    print('PT_LOAD 段:')
    for va0, va1, off, fs, ms, fl in segments:
        print('  VA 0x%08X..0x%08X  fileoff 0x%08X filesz 0x%X memsz 0x%X flags %d'
              % (va0, va1, off, fs, ms, fl))

    def seg_of(va):
        for va0, va1, off, fs, ms, fl in segments:
            if va0 <= va < va1:
                return 'VA 0x%X..0x%X' % (va0, va1)
        return '?'

    # ELF 的 ISO 范围
    f = [t for t in D['files'] if t['name'].startswith('SLUS_206.13')]
    if not f:
        print('!! 未在 ISO9660 里找到 SLUS_206.13')
        return 1
    elf_iso0, elf_iso1 = f[0]['iso_off'], f[0]['iso_end']
    print('SLUS_206.13: LBA %d ISO 0x%X..0x%X size %d'
          % (f[0]['lba'], elf_iso0, elf_iso1, f[0]['size']))

    runs = [(a, b) for a, b in D['runs'] if elf_iso0 <= (a + b) // 2 < elf_iso1]
    tot = sum(b - a for a, b in runs)
    print('\nELF 内差异游程 %d 个, 合计 %d B' % (len(runs), tot))

    # 按 gap 分组成"站点"
    groups = []
    for a, b in runs:
        if groups and a - groups[-1][1] <= x.group_gap:
            groups[-1][1] = max(groups[-1][1], b)
            groups[-1][2].append((a, b))
        else:
            groups.append([a, b, [(a, b)]])
    print('按 gap<=%d 分组成 %d 个站点' % (x.group_gap, len(groups)))
    L = []
    P = lambda s: (print(s), L.append(s))

    P('\n== P1 站点 (每个: ISO 范围 / VA 范围 / 字节数 / 所属段) ==')
    for i, (s, e, rs) in enumerate(groups):
        nb = sum(b - a for a, b in rs)
        P('  #%-3d ISO 0x%09X..0x%09X  VA 0x%08X..0x%08X  runs=%-4d bytes=%-6d %s'
          % (i, s, e, va_of_iso(s), va_of_iso(e), len(rs), nb, seg_of(va_of_iso(s))))

    P('\n== 逐 4 字节字对照 (只列与 EN 不同的字; VA = 指令地址) ==')
    P('  %-9s %-11s %-11s %-11s %s' % ('ISO', 'VA', 'EN', 'ZH', 'EN 反汇编'))
    seen = set()
    for a, b in runs:
        wa = a & ~3
        # 覆盖该游程的全部 4 字节字
        for w in range(wa, ((b + 3) & ~3), 4):
            if w in seen:
                continue
            seen.add(w)
            ea, eb = A[w:w + 4], B[w:w + 4]
            if ea == eb:
                continue
            P('  0x%07X 0x%08X %s %s'
              % (w, va_of_iso(w), ea.hex(), eb.hex()))
    P('\n★ 变化的 4 字节字总数 = %d' % len(seen))
    nz = sum(1 for w in seen if A[w:w + 4] != B[w:w + 4])
    P('★ 其中 EN≠ZH 的字 = %d' % nz)
    if x.out:
        with open(x.out, 'w', encoding='utf-8', newline='\n') as fo:
            fo.write('\n'.join(L) + '\n')
        print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
