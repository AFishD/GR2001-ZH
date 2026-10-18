# -*- coding: utf-8 -*-
r"""cvar_p1_table.py — 生成 P1 (ELF) 站点明细表 + 分类, 以及 P6 全项清单

用法: python cvar_p1_table.py --orig <EN.iso> --zh <ZH.iso> --components components.json
                             --outdir .
"""
import argparse
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
ELF_ISO_VA_ANCHOR = 0x93880
ELF_VA_BASE = 0x100000
va = lambda o: o - ELF_ISO_VA_ANCHOR + ELF_VA_BASE
iso = lambda v: v - ELF_VA_BASE + ELF_ISO_VA_ANCHOR

# 站点分类 (按 VA 区间判定, 依据 temp_elf.txt 的观察)
CATS = [
    (0x411690, 0x4116B0, 'B. 原盘全零区中新增代码 (cave)'),
    (0x416ED0, 0x417250, 'A. ★覆盖原盘既有代码的 cave 宿主区 (EN 侧是真代码)'),
    (0x417500, 0x4176F0, 'A. ★覆盖原盘既有代码的 cave 宿主区 (EN 侧是真代码)'),
    (0x565670, 0x565A50, 'B. 原盘全零区中新增代码 (cave)'),
    (0x577FA0, 0x578080, 'D. ELF 内字符串表 (EN ASCII → ZH GBK)'),
    (0x219B00, 0x21DA00, 'C. 字形带常量/立即数闸门改动 (0xFFB5→0x00B5 等)'),
]


def cat_of(v):
    for lo, hi, name in CATS:
        if lo <= v < hi:
            return name
    return 'E. 其它零散指令改动'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', required=True)
    ap.add_argument('--zh', required=True)
    ap.add_argument('--components', required=True)
    ap.add_argument('--outdir', default='.')
    ap.add_argument('--gap', type=int, default=64)
    x = ap.parse_args()
    C = json.load(open(x.components, encoding='utf-8'))
    A = open(x.orig, 'rb').read()
    B = open(x.zh, 'rb').read()
    runs = [tuple(r) for r in C['components']['P1_elf']['runs']]

    groups = []
    for a, b in runs:
        if groups and a - groups[-1][1] <= x.gap:
            groups[-1][1] = max(groups[-1][1], b)
            groups[-1][2].append((a, b))
        else:
            groups.append([a, b, [(a, b)]])

    words = []
    seen = set()
    for a, b in runs:
        for w in range(a & ~3, (b + 3) & ~3, 4):
            if w in seen:
                continue
            seen.add(w)
            if A[w:w + 4] != B[w:w + 4]:
                words.append((w, A[w:w + 4], B[w:w + 4]))

    L = []
    P = lambda s: (L.append(s), print(s))
    P('# P1 — ELF (`SLUS_206.13`) 补丁逐条明细')
    P('')
    P('- 来源: `GR_EN_ORIG.iso` vs `GR_ZH113b.iso` 逐字节对比')
    P('- ELF: ISO9660 LBA 295, ISO 0x%X..0x%X, %d B'
      % (295 * SEC, 295 * SEC + 37453732, 37453732))
    P('- 地址换算 (沿用仓库既有工具口径): **VA = ISO − 0x%X + 0x%X**'
      % (ELF_ISO_VA_ANCHOR, ELF_VA_BASE))
    P('- 差异游程 **%d** 个, 合计 **%d** B; 按 gap≤%d 归并为 **%d** 个"站点";'
      % (len(runs), sum(b - a for a, b in runs), x.gap, len(groups)))
    P('  变化的 4 字节字 **%d** 个 (全部 EN≠ZH)' % len(words))
    P('')
    P('## 站点表')
    P('')
    P('| # | ISO 范围 | VA 范围 | 游程 | 字节 | 分类 |')
    P('|---|---|---|---|---|---|')
    for i, (s, e, rs) in enumerate(groups):
        P('| %d | 0x%07X..0x%07X | 0x%08X..0x%08X | %d | %d | %s |'
          % (i, s, e, va(s), va(e), len(rs), sum(b - a for a, b in rs),
             cat_of(va(s))))
    P('')
    P('## 分类统计')
    P('')
    agg = {}
    for s, e, rs in groups:
        k = cat_of(va(s))
        nb = sum(b - a for a, b in rs)
        a = agg.setdefault(k, [0, 0, 0, s, e])
        a[0] += 1
        a[1] += len(rs)
        a[2] += nb
        a[3] = min(a[3], s)
        a[4] = max(a[4], e)
    P('| 分类 | 站点数 | 游程数 | 字节数 | ISO 范围 |')
    P('|---|---|---|---|---|')
    for k in sorted(agg, key=lambda z: -agg[z][2]):
        a = agg[k]
        P('| %s | %d | %d | %d | 0x%07X..0x%07X |' % (k, a[0], a[1], a[2], a[3], a[4]))
    P('')
    P('## 逐 4 字节字对照 (VA / EN / ZH)')
    P('')
    P('| # | ISO | VA | EN 4B | ZH 4B | 分类 |')
    P('|---|---|---|---|---|---|')
    for i, (w, ea, eb) in enumerate(words):
        P('| %d | 0x%07X | 0x%08X | `%s` | `%s` | %s |'
          % (i, w, va(w), ea.hex(), eb.hex(), cat_of(va(w))))
    P('')
    P('## 站点内容摘录 (每个站点前 12 个字)')
    P('')
    for i, (s, e, rs) in enumerate(groups):
        P('### 站点 %d — ISO 0x%07X..0x%07X / VA 0x%08X..0x%08X (%s)'
          % (i, s, e, va(s), va(e), cat_of(va(s))))
        P('')
        P('```')
        n = 0
        for w in range(s & ~3, (e + 3) & ~3, 4):
            if A[w:w + 4] == B[w:w + 4]:
                continue
            P('  ISO 0x%07X  VA 0x%08X  EN %s (%s)  ->  ZH %s (%s)'
              % (w, va(w), A[w:w + 4].hex(), _mn(A[w:w + 4]),
                 B[w:w + 4].hex(), _mn(B[w:w + 4])))
            n += 1
            if n >= 12:
                P('  ...')
                break
        P('```')
        P('')
    p1 = os.path.join(x.outdir, 'P1_ELF_SITES.md')
    with open(p1, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('→ %s' % p1)

    # ---- P6 全项清单
    comps = json.load(open(x.components, encoding='utf-8'))
    L2 = ['# P6 — 其它/未归类差异: 全项清单', '',
          'P6 共 **%d** 个结构, **%d** 个差异区间, **%d** 字节。'
          % (len(comps['components']['P6_other']['items']),
             len(comps['components']['P6_other']['runs']),
             comps['components']['P6_other']['bytes']), '',
          '> 这些差异**不属于** P1(ELF) / P2(字库图集) / P3(FONT.RES) / P4(三份文本容器)。',
          '> 逐项列出, 不含糊。', '',
          '| # | 结构 | 差异区间 | 字节 | ISO 范围 |', '|---|---|---|---|---|']
    items = sorted(comps['components']['P6_other']['items'].items(),
                   key=lambda kv: -kv[1]['bytes'])
    for i, (k, it) in enumerate(items):
        L2.append('| %d | %s | %d | %d | 0x%09X..0x%09X |'
                  % (i, k.replace('|', '/'), it['runs'], it['bytes'],
                     it['iso_lo'], it['iso_hi']))
    p6 = os.path.join(x.outdir, 'P6_ITEMS.md')
    with open(p6, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L2) + '\n')
    print('→ %s' % p6)
    return 0


def _mn(b):
    """MIPS 指令名（仅用 opcode/funct 粗略标注, 便于阅读）"""
    if b == b'\x00\x00\x00\x00':
        return 'nop'
    v = struct.unpack('<I', b)[0]
    op = v >> 26
    names = {0x00: 'SPECIAL', 0x02: 'j', 0x03: 'jal', 0x04: 'beq', 0x05: 'bne',
             0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi',
             0x0D: 'ori', 0x0F: 'lui', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
             0x27: 'sw', 0x28: 'sb', 0x29: 'sh', 0x2B: 'swc1', 0x31: 'lwc1',
             0x2F: 'cache'}
    if op == 0:
        fn = v & 0x3F
        f = {0x08: 'jr', 0x09: 'jalr', 0x20: 'add', 0x21: 'addu', 0x23: 'subu',
             0x24: 'and', 0x25: 'or', 0x2A: 'slt', 0x2B: 'sltu', 0x00: 'sll',
             0x02: 'srl', 0x03: 'sra', 0x18: 'mult', 0x1A: 'div'}
        return f.get(fn, 'SPECIAL/%d' % fn)
    return names.get(op, 'op0x%X' % op)


if __name__ == '__main__':
    sys.exit(main())
