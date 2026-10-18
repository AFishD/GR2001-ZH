# -*- coding: utf-8 -*-
r"""root_gsup2.py -- 反推 gsrunner 的 gsup_*.bin 真实结构（READ-ONLY）

gsrunner 里相关字符串: `gsup_%08x_%u.bin` / `GIF upload: ee=%08x size=%u -> %s`
所以转储 = **一段 EE 内存的原始拷贝**，`%08x` 是 EE 地址。文件长度 = size。

本工具：
  1. 打印头部字节与"若第一 16 B 是 header 则 ee/size"的解读
  2. 在文件里找已知 GIF tag 值（0x10000000 = PT/NREG1；0x08000000 = IMAGE regs）
  3. 用 NLOOP 反推：在**假设 16 B 头**下，用 0x08000000 tag 的 nloop 与后续数据长度对账
  4. 把 A+D (regs=0) 槽里的寄存器号/数据解出来（TEX0/TEX1/TRXPOS）
用法: python tools/re/toolbelt/root_gsup2.py <dir|file> [...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REG = {0x00: 'PRIM', 0x01: 'RGBAQ', 0x02: 'ST', 0x03: 'UV', 0x04: 'XYZF2', 0x05: 'XYZ2',
       0x06: 'TEX0_1', 0x07: 'TEX0_2', 0x08: 'CLAMP_1', 0x09: 'CLAMP_2', 0x0E: 'TRXPOS',
       0x0F: 'NOP', 0x13: 'FADE', 0x14: 'PRIM', 0x45: 'TEX1_1', 0x46: 'TEX1_2',
       0x49: 'XYOFFSET_1', 0x4A: 'XYOFFSET_2', 0x4C: 'PRMODECONT', 0x4D: 'PRMODE',
       0x4E: 'TEXCLUT', 0x53: 'SCISSOR_1', 0x54: 'SCISSOR_2', 0x55: 'ALPHA_1',
       0x56: 'ALPHA_2', 0x5C: 'TEST_1', 0x5D: 'TEST_2', 0x5F: 'FBA_1', 0x60: 'FBA_2',
       0x61: 'FRAME_1', 0x62: 'FRAME_2', 0x63: 'ZBUF_1', 0x64: 'ZBUF_2',
       0x65: 'BITBLTBUF', 0x66: 'SRCBUF', 0x67: 'TRXREG', 0x68: 'TRXDIR'}
KNOWN = {0x10000000: 'PT(regs=0x10000000)', 0x08000000: 'IMAGE(regs=0x08000000)',
         0x00000000: 'A+D(regs=0)'}


def tex0_fields(v):
    return dict(value='%016X' % v, TBP=v & 0x3FFF, TBW=(v >> 14) & 0x3F, PSM=(v >> 20) & 0x3F,
                TW=(v >> 26) & 0xF, TH=(v >> 30) & 0xF, TCC=(v >> 34) & 1,
                CBP=(v >> 37) & 0x3FFF, CPSM=(v >> 51) & 0xF, CSA=(v >> 56) & 0x1F)


def report(p):
    b = open(p, 'rb').read()
    print('=' * 100)
    print('%s   %d B (0x%X)' % (os.path.basename(p), len(b), len(b)))
    print('  [若 16 B 头] ee=0x%08X size=%d frame?=0x%08X' % tuple(
        list(struct.unpack_from('<3I', b, 0)) + [0])[:3])
    print('  head48: %s' % b[:48].hex(' '))
    # 找已知 tag 值（按 u32 对齐扫描，步长 4 太慢已够用）
    hits = {}
    for off in range(0, len(b) - 4, 4):
        w, = struct.unpack_from('<I', b, off)
        if w in KNOWN:
            hits.setdefault(w, []).append(off)
    for w, offs in sorted(hits.items()):
        print('  tag %08X (%s) x%d  前几处: %s  mod16=%s'
              % (w, KNOWN[w], len(offs), offs[:6], sorted(set(o % 16 for o in offs))[:6]))
    # 假定 16 B 头，从 off=16 起按 (tag:low, tag:high, data...) 走
    for start in (0x10, 0x00):
        off = start
        ev = []
        ok = True
        while off + 16 <= len(b):
            lo, hi = struct.unpack_from('<II', b, off)
            nloop = lo & 0x7FFF
            eop = (lo >> 15) & 1
            flg = (lo >> 58) & 3
            nreg = (lo >> 60) & 0xF
            if flg != 0 or nreg == 0:
                ok = False
                break
            nb = nloop * nreg * 16
            if off + 16 + nb > len(b):
                ev.append(('TRUNC', off, nloop, nreg, hi, nb, len(b) - off - 16))
                ok = False
                break
            ev.append(('P', off, nloop, nreg, hi, nb, 0))
            off += 16 + nb
        print('  --- 从 0x%X 起走包流: 事件 %d, 走到 0x%X, 干净结束=%s' % (start, len(ev), off, ok))
        if ev:
            regs = {}
            for e in ev:
                regs[e[4]] = regs.get(e[4], 0) + 1
            print('      regs 分布: %s' % {('%08X' % k): v for k, v in sorted(regs.items())})
            print('      前 6 个事件: %s' % [(e[0], hex(e[1]), e[2], e[3], '%08X' % e[4]) for e in ev[:6]])
    # A+D 槽解寄存器
    print('  --- A+D 槽扫描（找低字节 = 已知寄存器号的 16 B 槽）---')
    found = {}
    for off in range(0, len(b) - 16, 16):
        dlo, dhi = struct.unpack_from('<II', b, off)
        r = dlo & 0xFF
        if r in REG:
            found.setdefault(r, []).append((off, dlo >> 8, dhi))
    for r in sorted(found):
        v = found[r][:4]
        print('    reg 0x%02X %-12s x%-4d %s' % (r, REG[r], len(found[r]),
                                                 [(hex(o), '%08X' % d, '%08X' % h) for (o, d, h) in v]))
        if r in (0x06, 0x07):
            for (o, d, h) in found[r][:3]:
                t = tex0_fields(((d) | (h << 32)) & 0xFFFFFFFFFFFFFFFF)
                print('        TEX0=%s PSM=0x%X TW=%d(%d) TH=%d(%d) TBW=%d TBP=0x%X CBP=0x%X CPSM=0x%X'
                      % (t['value'], t['PSM'], t['TW'], 1 << t['TW'], t['TH'], 1 << t['TH'],
                         t['TBW'], t['TBP'], t['CBP'], t['CPSM']))
    return dict(size=len(b), found=found)


def main():
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            fs = sorted([os.path.join(a, f) for f in os.listdir(a) if f.startswith('gsup_')],
                        key=os.path.getsize)
            tot = 0
            for f in fs:
                r = report(f)
                tot += r['size']
            print('=' * 100)
            print('目录 %s: %d 个 gsup 转储, 合计 %d B' % (a, len(fs), tot))
            for f in fs:
                print('   %-28s %d' % (os.path.basename(f), os.path.getsize(f)))
        else:
            report(a)


main()
