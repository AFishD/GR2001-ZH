# -*- coding: utf-8 -*-
r"""p03_shortcut_tc.py — round42 步骤③: 解出 kShortcutDefaultTC (0x2BEFE0) 的「索引 → UV」表 (只读)

背景 (p02 扫描发现):
  .text 里唯一一处**同时**出现图标条 UV 常量 (198.0=0x4346 / 218.0=0x435A / 21.0=0x41A8)
  的、且不是 DrawString 的代码 = `kShortcutDefaultTC__FUii` @0x2BEFE0
  (源码符号名: kShortcutDefaultTC(unsigned int, int) → 返回 RSVector4 纹理坐标)。

  该函数是一张巨大的 switch: addiu v0,$zero,K ; beq a0,v0,<case>
  ⇒ 把 (K → UV 矩形) 全解出来, 就是**引擎的图标 UV 表**。

  DrawString v1 里那两个**文本图标码**的硬编码 UV 是同一张图集上的:
      0xB5 → (1,198)-(21,218)    0xB1 → (25,198)-(45,218)
  ⇒ 本表解出来后可以直接对照: 表里哪些 UV 与这两个重合 (即"文本码用的那张图")。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ELF = os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00
data = open(ELF, 'rb').read()
seg = data[SEC_OFF:SEC_OFF + SEC_SIZE]

FUNC = 0x2BEFE0
END = 0x2BFE10


def w(va):
    return struct.unpack_from('<I', seg, va - SEC_ADDR)[0]


def imm(w_):
    v = w_ & 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def fbits(hi):
    return struct.unpack('<f', struct.pack('<I', hi << 16))[0]


# ── ① 抓 switch 表: addiu v0,$zero,K  (紧跟着 beq a0,v0,target) ──
cases = {}
va = FUNC
while va < END:
    ww = w(va)
    # addiu rt, $zero, K
    if (ww >> 26) == 0x09 and ((ww >> 21) & 31) == 0 and ((ww >> 16) & 31) in (2, 4, 5):
        K = imm(ww)
        nxt = w(va + 4)
        if (nxt >> 26) == 0x04 and ((nxt >> 21) & 31) == 4:          # beq a0, rt, target
            tgt = va + 4 + 4 + (imm(nxt) << 2)
            cases.setdefault(K, tgt)
    va += 4

print('=' * 78)
print('kShortcutDefaultTC (0x%08X) switch: %d 个 case' % (FUNC, len(cases)))
print('=' * 78)

# ── ② 逐个 case: 扫到 jal __ct__9RSVector4Fffff 为止, 收集 mtc1 到 f12..f15 的常量 ──
FREG = {12: 'f12', 13: 'f13', 14: 'f14', 15: 'f15'}
rows = []
for K in sorted(cases):
    tgt = cases[K]
    f = {}
    q = tgt
    for _ in range(40):
        ww = w(q)
        if (ww >> 26) == 0x03:                              # jal → 结束
            break
        if ((ww >> 26) == 0x11) and (((ww >> 21) & 31) == 4):   # COP1 MTC1 rt, fs
            rt = (ww >> 16) & 31
            fs = (ww >> 11) & 31
            if fs in FREG and rt == 0:
                f[FREG[fs]] = 0.0
            elif fs in FREG and rt == 2:
                # 上一条 lui $v0, imm
                pw = w(q - 4)
                if (pw >> 26) == 0x0F and ((pw >> 16) & 31) == 2:
                    f[FREG[fs]] = fbits(pw & 0xFFFF)
        q += 4
    vals = [f.get(k) for k in ('f12', 'f13', 'f14', 'f15')]
    if all(v is not None for v in vals):
        rows.append((K, vals))
        print('  idx %-3d → (%.0f, %.0f) - (%.0f, %.0f)'
              % (K, vals[0], vals[1], vals[2], vals[3]))
    else:
        print('  idx %-3d → **非常量** (走别的分支: 运行时状态)  %s' % (K, vals))

print()
print('=' * 78)
print('对照: DrawString v1 文本图标码的硬编码 UV')
print('=' * 78)
print('  0xB5 → (1, 198) - (21, 218)')
print('  0xB1 → (25, 198) - (45, 218)')
print()
print('  表里 UV 落在 y∈[178,218] 的 (同一图标条):')
for K, v in rows:
    if 170 <= v[1] <= 220 or 170 <= v[3] <= 220:
        print('    idx %-3d (%.0f, %.0f) - (%.0f, %.0f)  %s'
              % (K, v[0], v[1], v[2], v[3],
                 '★ 与文本码同一带' if abs(v[1] - 198) < 1 or abs(v[1] - 178) < 1 else ''))
print()
print('  表里 y 明显不同 (= 另一张图集/另一段) 的:')
for K, v in rows:
    if not (170 <= v[1] <= 220 or 170 <= v[3] <= 220):
        print('    idx %-3d (%.0f, %.0f) - (%.0f, %.0f)' % (K, v[0], v[1], v[2], v[3]))
