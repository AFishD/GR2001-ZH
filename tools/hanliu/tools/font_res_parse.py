#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: gr_tools/font_res_parse.py (逐字复制 (探针脚本, 顶层执行, 不可 import))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""font_res_parse.py - 精确解析 FONT.RES(new_font_revised.rsb) 全部 face 结构
文件: {u32 namelen}{"new_font_revised.rsb"}{u32 3}{u32 5}
      {face 块}* {尾部绑定表}
face 块: {"name\x0a"}{u32 头...}{f32 对(atlas 宽,高?)}{u32 base=0x20}{u32 行高}
      {10B 记录}* {x0,y0,x1,y1,tag} = 字符 base+i 的字形矩形
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct

path = os.path.join(REPO_ROOT, 'docs', 'han_v2', 'artifacts', 'font_rsfb_engine.bin')
buf = open(path, 'rb').read()
n = len(buf)
print('file %d bytes' % n)

# 1. 找全部 face 名标记
names = []
for nm in (b'large\x0a', b'default\x0a', b'huge\x0a', b'PC\x0a'):
    p = 0
    while True:
        j = buf.find(nm, p)
        if j < 0:
            break
        names.append((j, nm[:-1].decode()))
        p = j + 1
names.sort()
print('\n== face 名标记 ==')
for j, nm in names:
    print('  0x%04x %s' % (j, nm))

def u32(a):
    return struct.unpack_from('<I', buf, a)[0]

def f32(a):
    return struct.unpack_from('<f', buf, a)[0]

# 2. 对每个标记, 解析其后的头 + 记录运行
print('\n== face 块解析 ==')
for k, (j, nm) in enumerate(names):
    hdr = j + len(nm) + 1  # 跳过 name\x0a
    h = [u32(hdr + 4 * i) for i in range(4)]
    # f32 对: 在头后 0x20 字节内搜 LE u32 0x44000000 或 0x43d00000 等
    fpos = []
    for o in range(hdr, hdr + 0x24, 1):
        v = u32(o)
        if 0x43000000 <= v <= 0x45000000 and (v & 0xFFFF) == 0:
            if not fpos or o - fpos[-1] > 3:
                fpos.append(o)
    base = None
    for o in range(hdr, hdr + 0x30, 4):
        if u32(o) == 0x20:
            base = o
            break
    print('  [0x%04x] %s hdr@0x%x u32=%s f32@%s base@%s' %
          (j, nm, hdr, h, [(hex(p), f32(p)) for p in fpos], hex(base) if base else None))
    # 记录起点: base 之后的第一个合法 10B 记录
    start = (base + 4) if base else hdr + 0x20
    # 对齐到记录: 逐字节试
    rec_start = None
    for s in range(start, start + 8):
        x0, y0, x1, y1, tag = struct.unpack_from('<5H', buf, s)
        if 0 <= x0 < x1 <= 512 and y1 - y0 in (26,) and tag < 0x8000:
            rec_start = s
            break
    if rec_start is None:
        print('    (无记录)')
        continue
    # 数记录
    cnt = 0
    ys = {}
    p = rec_start
    while p + 10 <= n:
        x0, y0, x1, y1, tag = struct.unpack_from('<5H', buf, p)
        if not (0 <= x0 < x1 <= 512 and 0 < y1 <= 512 and y0 < y1 and tag < 0x8000):
            break
        ys[(y0, y1)] = ys.get((y0, y1), 0) + 1
        cnt += 1
        p += 10
    print('    记录 0x%x..0x%x 共 %d 条, (y0,y1)=%s' %
          (rec_start, p, cnt, dict(sorted(ys.items()))))

# 3. PAK 头部
pak = open(os.path.join(REPO_ROOT, 'docs', 'han_v2', 'artifacts', 'COMMON_PAK.bin'), 'rb').read()
print('\n== COMMON.PAK 头 0x1040..0x1080 ==')
for p in range(0x1040, 0x1080, 16):
    row = pak[p:p+16]
    print('  %04x: %s  %s' % (p, row.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))
print('PAK 总长:', len(pak))
