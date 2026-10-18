# -*- coding: utf-8 -*-
"""r50: 在英文原盘里直接按字节找 T0039 的原文 (+ or - 10 meters)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso')
NEEDLES = [b'with an accuracy of + or - 10 meters',
           b'accuracy of + or - 10',
           b'+ or - 10 meters',
           b'AN/GVS-5']
CHUNK = 1 << 22
OVER = 256
hits = {n: [] for n in NEEDLES}
pos = 0
tail = b''
n_b1 = 0
with open(ISO, 'rb') as f:
    while True:
        buf = f.read(CHUNK)
        if not buf:
            break
        n_b1 += buf.count(b'\xb1')
        blob = tail + buf
        base = pos - len(tail)
        for n in NEEDLES:
            st = 0
            while True:
                i = blob.find(n, st)
                if i < 0:
                    break
                hits[n].append(base + i)
                st = i + 1
        tail = blob[-OVER:]
        pos += len(buf)
print('ISO 大小 %d B; 全盘字节 0xB1 (latin-1 的 ±) 出现 %d 次' % (pos, n_b1))
for n in NEEDLES:
    print('%-46r -> %d 处 %s' % (n, len(hits[n]), hits[n][:4]))
# 打印命中附近的上下文
if hits[NEEDLES[0]]:
    off = hits[NEEDLES[0]][0]
    with open(ISO, 'rb') as f:
        f.seek(max(0, off - 160))
        ctx = f.read(360)
    print('上下文 (latin-1):')
    print(repr(ctx.decode('latin-1')))
