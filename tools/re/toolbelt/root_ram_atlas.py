# -*- coding: utf-8 -*-
r"""root_ram_atlas.py -- 在 eeram.bin / iopram.bin 里找「图集容器/像素缓冲」在 RAM 中的真实形态（READ-ONLY）

做法:
  · 用 16 B 对齐、小端 u32/u64 扫描出「GIF PACKED tag 形状」的 16 B 块
    （flg=0(PACKED), nreg!=0, nloop 合理），打印偏移 + 解出的字段
  · 再找长串 0x11 的候选像素缓冲
用法: python tools/re/toolbelt/root_ram_atlas.py <bin> [<bin> ...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def decode(lo, hi):
    return dict(nloop=lo & 0x7FFF, eop=(lo >> 15) & 1, pre=(lo >> 46) & 1,
                prim=(lo >> 47) & 0x7FF, flg=(lo >> 58) & 3, nreg=(lo >> 60) & 0xF,
                regs=hi)


def main():
    for path in sys.argv[1:]:
        sz = os.path.getsize(path)
        with open(path, 'rb') as f:
            d = f.read()
        print('=' * 100)
        print('%s  (%d B = 0x%X)' % (path, sz, sz))
        # 1) 全盘找 nreg!=0 且 flg==0 的 PACKED tag
        hits = []
        for off in range(0, sz - 16, 16):
            lo, hi = struct.unpack_from('<II', d, off)
            if lo == 0 and hi == 0:
                continue
            t = decode(lo, hi)
            if t['flg'] == 0 and t['nreg'] != 0 and 0 < t['nloop'] <= 0x7FFF and lo != 0x11111111:
                hits.append((off, t))
        print('  PACKED-tag 候选 %d 个' % len(hits))
        for (off, t) in hits[:60]:
            print('    0x%08X  nloop=%-6d eop=%d nreg=0x%X regs=%08X prim=0x%X'
                  % (off, t['nloop'], t['eop'], t['nreg'], t['regs'], t['prim']))
        if len(hits) > 60:
            print('    ... +%d' % (len(hits) - 60))
        # 2) 找最长的 0x11 游程
        best = (0, 0)
        i = 0
        while i < sz:
            if d[i] == 0x11:
                j = i
                while j < sz and d[j] == 0x11:
                    j += 1
                if j - i > best[1]:
                    best = (i, j - i)
                i = j
            else:
                i += 1
        print('  最长 0x11 游程: @0x%X 长 %d B (0x%X)' % (best[0], best[1], best[1]))
        # 3) 找 0x11 游程里是否夹着含 nloop 的 tag（= 像素缓冲带 tag 的证据）
        needle = struct.pack('<I', 0x00008800)     # IMAGE tag lo (nloop=0, eop=1) 形态之一
        pos = d.find(needle)
        n = 0
        while pos >= 0 and n < 20:
            print('  IMAGEtag-lo(0x00008800) 命中 @0x%X' % pos)
            pos = d.find(needle, pos + 1)
            n += 1


main()
