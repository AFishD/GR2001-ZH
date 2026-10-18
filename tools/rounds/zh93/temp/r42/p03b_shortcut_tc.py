# -*- coding: utf-8 -*-
r"""p03b_shortcut_tc.py — round42: 正确解出 kShortcutDefaultTC (0x2BEFE0) 的「索引 → UV」表

修 p03 的缺陷: p03 只看了紧邻的上一条 lui ⇒ 漏掉编译器插在中间的指令,
且分支体里可能有**两组** UV (运行时状态决定)。本脚本改为:
  · 逐条走, 维护「CPU 寄存器 → 最近一次 lui 的立即数」;
  · 每遇到 mtc1 rc, $fN 就记 f[N] = regval[rc] (或 0 若 rc=$zero);
  · 每遇到 jal (RSVector4 ctor) 就把当前 f12..f15 记为一组, 然后清空;
  ⇒ 一个 case 里有多组就全部列出 (那是"按运行时状态二选一")。
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
R = ['$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3', '$t0', '$t1', '$t2', '$t3',
     '$t4', '$t5', '$t6', '$t7', '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
     '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra']


def w(va):
    return struct.unpack_from('<I', seg, va - SEC_ADDR)[0]


def simm(x):
    return x - 0x10000 if x >= 0x8000 else x


def fbits(hi):
    return struct.unpack('<f', struct.pack('<I', hi << 16))[0]


# ── ① switch 表: addiu Rt,$zero,K + beq a0,Rt,target ──
cases, va = {}, FUNC
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
print('kShortcutDefaultTC @0x%08X — switch case 表 (%d 个索引)' % (FUNC, len(cases)))
print('=' * 78)


def scan(tgt, limit=64):
    """从 case 起点扫到 limit 条, 返回 [(f12,f13,f14,f15, 结束地址)] 组列表。"""
    reg, f, out = {}, {}, []
    for i in range(limit):
        q = tgt + 4 * i
        ww = w(q)
        op = ww >> 26
        if op == 0x0F:                                     # lui rt, imm
            reg[(ww >> 16) & 31] = fbits(ww & 0xFFFF)
        elif op == 0x11 and ((ww >> 21) & 31) == 4:        # mtc1 rc, fs
            rc, fs = (ww >> 16) & 31, (ww >> 11) & 31
            f[fs] = 0.0 if rc == 0 else reg.get(rc)
        elif op == 0x03:                                   # jal
            got = tuple(f.get(k) for k in (12, 13, 14, 15))
            if any(v is not None for v in got):
                out.append((got, q))
            f = {}
            if len(out) >= 3:
                break
        elif op in (0x02,):                                # j
            break
    return out


allrows = {}
for K in sorted(cases):
    res = scan(cases[K])
    allrows[K] = res
    print('  idx %-3d (case @0x%08X):' % (K, cases[K]))
    if not res:
        print('         (没找到常量 UV —— 由别处赋值)')
    for got, q in res:
        a, b, c, d = got
        txt = ' / '.join('?' if v is None else ('%.0f' % v) for v in got)
        box = ('(%.0f, %.0f) - (%.0f, %.0f)' % (a, b, c, d)
               if all(v is not None for v in got) else '不完整: %s' % txt)
        print('         jal@0x%08X  UV = %s' % (q, box))

print()
print('=' * 78)
print('对照: DrawString v1 (0x219A70) 里两个**文本图标码**的硬编码 UV')
print('=' * 78)
print('  0xB5 → (1, 198) - (21, 218)')
print('  0xB1 → (25, 198) - (45, 218)')
print()
same = [(K, r) for K, rs in allrows.items() for (r, _q) in rs
        if all(v is not None for v in r) and
        ((abs(r[1] - 198) < 0.6 and abs(r[3] - 218) < 0.6)
         or (abs(r[1] - 178) < 0.6 and abs(r[3] - 198) < 0.6))]
print('  与本表 UV 处于同一图标条 (v ∈ {178..198, 198..218}) 的索引:')
for K, r in same:
    print('    idx %-3d (%.0f, %.0f) - (%.0f, %.0f)' % (K, r[0], r[1], r[2], r[3]))
if not same:
    print('    (无 —— 说明文本码那张图与 kShortcut 表不是同一张纹理)')
