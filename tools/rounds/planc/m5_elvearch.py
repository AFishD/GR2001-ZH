# -*- coding: utf-8 -*-
r"""m5_elvearch.py — 在 ELF 里搜「每行相位表」PHI = [6,6,6,6,12,12,12,12,18,18,18,18,24,30,...,2]

若引擎有一张 24 行的相位表, 就该能在 ELF 里找到它的字节/半字/字形态。
另: 打印 4 处 gate 的当前值, 确认现役盘 ELF 的 lead 上界。
只读。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')

PHI = [6, 6, 6, 6, 12, 12, 12, 12, 18, 18, 18, 18, 24,
       30, 30, 30, 30, 36, 36, 2, 2, 2, 2, 2]

data = open(ISO, 'rb').read(12 << 20)          # 前 12 MB (ELF + 表)
print('读入 %d B' % len(data))

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


print()
print('== 4 处 gate 现值 ==')
for va, desc in ((0x416EE8, 'DrawString 取码'), (0x417160, 'StringWidth 头'),
                 (0x41751C, 'DoWordWrap 逐字'), (0x5656A4, 'StringWidth 尾')):
    o = elf_off(va)
    w = struct.unpack_from('<I', data, o)[0]
    print('  0x%06X %-18s = %08X' % (va, desc, w))

print()
print('== 相位表搜索 ==')
pats = {
    'bytes': bytes(PHI),
    'shorts_le': b''.join(struct.pack('<H', v) for v in PHI),
    'words_le': b''.join(struct.pack('<I', v) for v in PHI),
    'pix_bytes_16': bytes(v * 16 for v in PHI if v * 16 < 256),
    'pix_shorts': b''.join(struct.pack('<H', v * 16) for v in PHI),
}
for name, pat in pats.items():
    pos, hits = 0, []
    while True:
        i = data.find(pat, pos)
        if i < 0:
            break
        hits.append(i)
        pos = i + 1
    # 该模式在 ELF 内的 VA
    vas = []
    for h in hits:
        if h >= ELF_LBA * 2048:
            vas.append(hex(SEC_ADDR + h - ELF_LBA * 2048 - SEC_OFF))
    print('  %-16s 命中 %2d 处  file=%s  va=%s'
          % (name, len(hits), [hex(h) for h in hits[:6]], vas[:6]))

print()
print('== 相位表的后半段搜索 (只搜 24→30→30→30→30→36→36→2) ==')
sub = PHI[12:]
for name, pat in (('bytes', bytes(sub)),
                  ('shorts', b''.join(struct.pack('<H', v) for v in sub)),
                  ('pix_shorts', b''.join(struct.pack('<H', v * 16) for v in sub))):
    pos, hits = 0, []
    while True:
        i = data.find(pat, pos)
        if i < 0:
            break
        hits.append(i)
        pos = i + 1
    print('  %-12s 命中 %d 处 %s' % (name, len(hits), [hex(h) for h in hits[:8]]))

print()
print('== 尾部独特序列 2,2,2,2,2 (5 个连续 2) ==')
for name, pat in (('bytes', bytes([2] * 5)), ('shorts', struct.pack('<5H', *([2] * 5)))):
    n = data.count(pat)
    print('  %-8s 出现 %d 次 (太常见, 无意义)' % (name, n))
