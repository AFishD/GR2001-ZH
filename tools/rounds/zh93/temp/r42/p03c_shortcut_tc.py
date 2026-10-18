# -*- coding: utf-8 -*-
r"""p03c_shortcut_tc.py — round42: kShortcutDefaultTC 索引→UV 表 (按 case 体边界精确切分)

切分口径: switch 的每个 case 体 = 从 case 目标地址起, 到**第一条** `beq $zero,$zero,epilogue`
(= 0x2BFE0C, 编译器给 case 收尾的 j 指令) 为止。idx 0 由 `beq a0,$zero,0x2BF0E4` 直接给出。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ELF = os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00
seg = open(ELF, 'rb').read()[SEC_OFF:SEC_OFF + SEC_SIZE]
FUNC, END = 0x2BEFE0, 0x2BFE10


def w(va):
    return struct.unpack_from('<I', seg, va - SEC_ADDR)[0]


def simm(x):
    return x - 0x10000 if x >= 0x8000 else x


def fbits(hi):
    return struct.unpack('<f', struct.pack('<I', hi << 16))[0]


def is_epi_jump(ww, va):
    return (ww >> 26) == 4 and ((ww >> 21) & 31) == 0 and ((ww >> 16) & 31) == 0 \
        and va + 4 + (simm(ww & 0xFFFF) << 2) == 0x2BFE0C


def is_branch(ww):
    return (ww >> 26) in (4, 5, 6, 1, 7) or ((ww >> 26) == 0 and (ww & 63) in (0x09, 0x0A, 0x0B))


cases, va = {0: 0x2BF0E4}, FUNC
while va < END:
    ww = w(va)
    if (ww >> 26) == 0x09 and ((ww >> 21) & 31) == 0:
        rt = (ww >> 16) & 31
        K = simm(ww & 0xFFFF)
        nxt = w(va + 4)
        if ((nxt >> 26) == 0x04 and ((nxt >> 16) & 31) == rt
                and ((nxt >> 21) & 31) == 4 and 0 <= K <= 64):
            cases.setdefault(K, va + 4 + 4 + (simm(nxt & 0xFFFF) << 2))
    va += 4

print('=' * 78)
print('kShortcutDefaultTC @0x%08X — 共 %d 个索引的 case' % (FUNC, len(cases)))
print('=' * 78)

table = {}
for K in sorted(cases):
    tgt = cases[K]
    reg, f, groups, conds = {}, {}, [], []
    q = tgt
    while q < END:
        ww = w(q)
        if is_epi_jump(ww, q):
            got = tuple(f.get(k) for k in (12, 13, 14, 15))
            if any(v is not None for v in got):
                groups.append((got, q, list(conds)))
            break
        op = ww >> 26
        if op == 0x0F:
            reg[(ww >> 16) & 31] = fbits(ww & 0xFFFF)
        elif op == 0x11 and ((ww >> 21) & 31) == 4:
            rc, fs = (ww >> 16) & 31, (ww >> 11) & 31
            if fs in (12, 13, 14, 15):
                f[fs] = 0.0 if rc == 0 else reg.get(rc)
        elif op == 0x03:
            got = tuple(f.get(k) for k in (12, 13, 14, 15))
            if any(v is not None for v in got):
                groups.append((got, q, list(conds)))
            f = {}
        elif is_branch(ww):
            conds.append('%08X:%08X' % (q, ww))
        q += 4
    table[K] = groups
    print('  idx %-3d (case @0x%08X, %d 组):' % (K, tgt, len(groups)))
    for got, q, conds in groups:
        if all(v is not None for v in got):
            print('       jal@0x%08X  UV = (%.0f, %.0f) - (%.0f, %.0f)%s'
                  % (q, got[0], got[1], got[2], got[3],
                     '   [前置分支 %d 个]' % len(conds) if conds else ''))
        else:
            print('       jal@0x%08X  UV = %s' % (q, got))

print()
print('=' * 78)
print('DrawString v1 的**文本图标码**硬编码 UV (同一张字体图集)')
print('=' * 78)
print('  0xB5 → (1, 198) - (21, 218)')
print('  0xB1 → (25, 198) - (45, 218)')
