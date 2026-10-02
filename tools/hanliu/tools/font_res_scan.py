#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: gr_tools/font_res_scan.py (逐字复制 (记录边界扫描))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""font_res_scan.py - 扫描 FONT.RES 解码流(font_rsfb_engine.bin)的 10B 记录组边界

记录 = {u16 code, u16 z, u16 next, u16 h, u16 param}
约束: code <= next, h ∈ 已知组高集合, param < 0x8000
输出: 每个连续合法记录段的 [起, 止) 偏移 + 首尾记录 + h/param 分布
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

path = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(REPO_ROOT, 'docs', 'han_v2', 'artifacts', 'font_rsfb_engine.bin')
buf = open(path, 'rb').read()
print('file:', len(buf), 'bytes')

def rec(p):
    return struct.unpack_from('<5H', buf, p)

def plausible(code, z, nxt, h, prm):
    if code > nxt or nxt > 0x1000:
        return False
    if prm >= 0x8000:
        return False
    return True

# 先做无假设的逐 10B 滑动: 标记每个偏移处"看起来像记录"的分数
runs = []
p = 0x5f
cur_start = None
while p + 10 <= len(buf):
    code, z, nxt, h, prm = rec(p)
    ok = plausible(code, z, nxt, h, prm)
    if ok:
        if cur_start is None:
            cur_start = p
    else:
        if cur_start is not None:
            runs.append((cur_start, p))
            cur_start = None
    p += 10
if cur_start is not None:
    runs.append((cur_start, p))

print('\n== 连续合法记录段 ==')
for a, b in runs:
    n = (b - a) // 10
    hs = {}
    prms = []
    for q in range(a, b, 10):
        code, z, nxt, h, prm = rec(q)
        hs[h] = hs.get(h, 0) + 1
        if len(prms) < 4 or q + 10 >= b:
            prms.append((hex(q), code, z, nxt, h, hex(prm)))
    print('段 0x%x..0x%x  %d 条  h分布=%s' % (a, b, n, hs))
    for r in prms[:6]:
        print('    @%s code=%d z=%d next=%d h=%d param=%s' % r)

# 细看 h=26 组逐条直到首个可疑处
print('\n== h=26 组(0x5f 起)逐条 ==')
p = 0x5f
i = 0
while p + 10 <= len(buf):
    code, z, nxt, h, prm = rec(p)
    if not plausible(code, z, nxt, h, prm):
        print('  0x%04x 停止: %s' % (p, (code, z, nxt, h, hex(prm))))
        break
    if i < 6 or (code >= 0x20 and code <= 0x7f and (i % 8 == 0)):
        print('  0x%04x #%3d code=%3d(0x%02x) z=%d next=%3d h=%d param=0x%04x' %
              (p, i, code, code, z, nxt, h, prm))
    p += 10
    i += 1
print('h=26 组: 0x5f .. 0x%x  共 %d 条 (结束偏移 0x%x)' % (p, i, p))

# 全文件 h 值直方图(10B 对齐, 自 0x5f)
print('\n== 全文件 h 字段直方图(0x5f 起 10B 对齐) ==')
from collections import Counter
cnt = Counter()
q = 0x5f
while q + 10 <= len(buf):
    cnt[rec(q)[3]] += 1
    q += 10
for h, c in sorted(cnt.items()):
    print('  h=%5d(0x%04x): %d' % (h, h, c))
