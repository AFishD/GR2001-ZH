# -*- coding: utf-8 -*-
r"""ab5_xref.py — 任务 1-C: cave 落点 xref 扫描 (只读)

对 cave 覆盖的符号做**三类**引用扫描 (EN 原盘 + ZH 盘各一遍):
  ① `jal T` / `j T`                —— 直接调用 (26 位立即数精确匹配)
  ② `jal`/`j` 落到**被覆盖区间内部**的任意地址 (不只入口)
  ③ `lui+addiu` / `lui+ori` 构造出的**立即数地址** == T   (函数指针/数据引用)
产出 evidence/C_cave_xref.md / C_cave_xref.json
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 被 cave 覆盖/使用的符号入口 (VA) —— 来自 A_offset_table.json 的 cave 类 run
CAVE = [
    ('sceRemove', 0x416ED0), ('sceMkdir', 0x416EF0), ('sceFormat', 0x4170C0),
    ('sceDopen', 0x417470), ('sceDclose', 0x417538), ('sceIpuInit', 0x411458),
    ('strlwr', 0x407060), ('strupr', 0x408910),
    ('sceDread', 0x4176A0),
]
STRS = [('@5689', 0x577FA0), ('@5690', 0x577FC0), ('@5694', 0x578010),
        ('@5695', 0x578028), ('@5696', 0x578040), ('@5698', 0x578068)]
# 汉化自己 jal/j 过去的 cave 入口 (用来验证"hook 目标本身无原盘调用")
HOOKS = [('cave@416ED0', 0x416ED0), ('cave@416F40', 0x416F40), ('cave@417050', 0x417050),
         ('cave@417150', 0x417150), ('cave@417200', 0x417200), ('cave@417500', 0x417500),
         ('cave@417600', 0x417600), ('cave@417650', 0x417650), ('cave@417680', 0x417680),
         ('cave@4176A0', 0x4176A0), ('cave@4176B0', 0x4176B0),
         ('cave@565670', 0x565670), ('cave@565730', 0x565730), ('cave@565760', 0x565760),
         ('cave@56583C', 0x56583C), ('cave@565900', 0x565900), ('cave@565930', 0x565930),
         ('cave@565A00', 0x565A00), ('cave@411690', 0x411690)]


def jxx_hits(e, lo, hi):
    """扫 [lo,hi) 内所有 jal/j 指令 → [(va, 'jal'|'j', target)]"""
    ph = [p for p in e.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
    o0, o1 = ph['off'], ph['off'] + ph['filesz']
    out = []
    for o in range(o0 & ~3, o1 - 3, 4):
        w = struct.unpack_from('<I', e.b, o)[0]
        op = w >> 26
        if op in (2, 3):
            t = (w & 0x3FFFFFF) << 2
            if lo <= t < hi:
                out.append((e.off2va(o)[0], 'jal' if op == 3 else 'j', t))
    return out


def imm_refs(e, targets):
    """扫 lui+addiu / lui+ori 立即数构造 → {target: [(va, 'lui/addiu'|'lui/ori', text)]}"""
    ph = [p for p in e.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
    o0, o1 = ph['off'], ph['off'] + ph['filesz']
    tset = set(targets)
    out = {}
    for o in range(o0 & ~3, o1 - 3, 4):
        w = struct.unpack_from('<I', e.b, o)[0]
        if (w >> 26) != 0x0F:
            continue
        rt = (w >> 16) & 0x1F
        hi = w & 0xFFFF
        for k in range(1, 9):
            o2 = o + 4 * k
            if o2 + 4 > o1:
                break
            w2 = struct.unpack_from('<I', e.b, o2)[0]
            op2 = w2 >> 26
            if op2 not in (0x09, 0x0D):            # addiu / ori
                continue            # ★ 只要**基址寄存器**是那个 lui 的目标即可; 目的寄存器可以不同
            #   (本盘实际写法: `lui v0,0x57 ; addiu s7,v0,0x7FA0`)
            if ((w2 >> 21) & 0x1F) != rt:
                continue
            lo = w2 & 0xFFFF
            if op2 == 0x09:
                slo = lo - 0x10000 if lo & 0x8000 else lo
                val = (hi << 16) + slo
                kind = 'lui/addiu'
            else:
                val = (hi << 16) | lo
                kind = 'lui/ori'
            val &= 0xFFFFFFFF
            if val in tset:
                out.setdefault(val, []).append((e.off2va(o)[0], kind, k))
    return out


def main():
    e_en, _ = A.load_elf('EN_ORIG')
    e_zh, _ = A.load_elf('ZH113b')
    buf = io.StringIO()
    W = buf.write
    data = {}
    W('# C) cave 落点 xref 扫描\n\n')
    W('对 **英文原盘** 与 **GR_ZH113b** 各扫一遍。三类引用: ① `jal/j` 入口 '
      '② `jal/j` 落到被覆盖区间内任意地址 ③ `lui+addiu/ori` 立即数构造出的地址。\n\n')

    # ---- 1) 符号入口 ----
    W('## C.1 被 cave 覆盖的符号入口 —— 直接调用者\n\n')
    W('| 符号 | 入口 VA | EN 盘 `jal/j` | ZH 盘 `jal/j` | 是否活引用 |\n|---|---|---|---|---|\n')
    live = {}
    for (nm, va) in CAVE:
        a = [x for x in jxx_hits(e_en, va, va + 4)]
        b = [x for x in jxx_hits(e_zh, va, va + 4)]
        live[nm] = dict(entry=va, en=[list(x) for x in a], zh=[list(x) for x in b])
        W('| `%s` | 0x%X | %d %s | %d %s | %s |\n'
          % (nm, va, len(a), ' '.join('0x%X' % x[0] for x in a),
             len(b), ' '.join('0x%X' % x[0] for x in b),
             '★ **活引用**' if a else '无（死代码）'))
    W('\n')

    # ---- 2) 区间内部 ----
    W('## C.2 `jal/j` 落到**被覆盖区间内部**的任意地址\n\n')
    RANGES = {
        'strlwr 覆盖区': (0x407078, 0x407097),
        'strupr 覆盖区': (0x408928, 0x408947),
        'sceIpuInit cave': (0x411690, 0x4116A8),
        'sceRemove/sceMkdir 前段 cave': (0x416ED0, 0x41713C),
        'sceFormat cave': (0x417150, 0x41721B),
        'sceDopen cave': (0x417500, 0x4175C0),
        'sceDclose/sceDread cave': (0x417600, 0x4176E8),
    }
    W('| 区间 | VA 范围 | EN `jal/j` 命中 | ZH `jal/j` 命中 |\n|---|---|---|---|\n')
    data['ranges'] = {}
    for nm, (lo, hi) in RANGES.items():
        a = jxx_hits(e_en, lo, hi)
        b = jxx_hits(e_zh, lo, hi)
        data['ranges'][nm] = dict(lo=lo, hi=hi, en=[list(x) for x in a], zh=[list(x) for x in b])
        W('| %s | 0x%X..0x%X | %d %s | %d %s |\n'
          % (nm, lo, hi, len(a),
             '<br>'.join('0x%X→0x%X(%s)' % (x[0], x[2], x[1]) for x in a) or '—',
             len(b),
             '<br>'.join('0x%X→0x%X(%s)' % (x[0], x[2], x[1]) for x in b) or '—'))
    W('\n')

    # ---- 3) 立即数引用 ----
    W('## C.3 立即数构造 (`lui+addiu` / `lui+ori`) 指向被覆盖地址的站点\n\n')
    tgt_entries = [va for (_, va) in CAVE] + [va for (_, va) in STRS]
    tgt_ranges = []
    for nm, (lo, hi) in RANGES.items():
        tgt_ranges += list(range(lo, hi, 4))
    allt = sorted(set(tgt_entries + tgt_ranges))
    for tag, e in (('EN_ORIG', e_en), ('ZH113b', e_zh)):
        r = imm_refs(e, allt)
        W('### %s\n\n' % tag)
        if not r:
            W('  **0 处**\n\n')
        for val in sorted(r):
            W('  - 0x%X ← %s\n' % (val, ', '.join('0x%X(%s,+%d)' % x for x in r[val])))
        W('\n')
        data['imm_%s' % tag] = {hex(k): [list(x) for x in v] for k, v in r.items()}

    # ---- 4) 字符串引用 (专项) ----
    W('## C.4 `@5689..@5698` 多语言 loading 字符串的引用者\n\n')
    W('| 符号 | VA | EN `lui+addiu/ori` | ZH 同 |\n|---|---|---|---|\n')
    for (nm, va) in STRS:
        a = imm_refs(e_en, [va]).get(va, [])
        b = imm_refs(e_zh, [va]).get(va, [])
        W('| `%s` | 0x%X | %d %s | %d %s |\n'
          % (nm, va, len(a), ' '.join('0x%X' % x[0] for x in a),
             len(b), ' '.join('0x%X' % x[0] for x in b)))
    W('\n')

    # ---- 5) 汉化自身新增的调用 ----
    W('## C.5 汉化新增的 `jal/j`（EN 无 → ZH 有）\n\n')
    W('| 目标 | EN | ZH | 新增调用点 |\n|---|---|---|---|\n')
    for (nm, va) in CAVE + HOOKS:
        a = set(x[0] for x in jxx_hits(e_en, va, va + 4))
        b = set(x[0] for x in jxx_hits(e_zh, va, va + 4))
        W('| `%s` 0x%X | %d | %d | %s |\n'
          % (nm, va, len(a), len(b),
             ' '.join('0x%X' % x for x in sorted(b - a)) or '—'))
    W('\n')

    data['symbols'] = {nm: dict(entry=va, en=[list(x) for x in jxx_hits(e_en, va, va + 4)],
                                zh=[list(x) for x in jxx_hits(e_zh, va, va + 4)])
                       for (nm, va) in CAVE}
    data['strings'] = {nm: dict(va=va, en=[list(x) for x in imm_refs(e_en, [va]).get(va, [])],
                                zh=[list(x) for x in imm_refs(e_zh, [va]).get(va, [])])
                       for (nm, va) in STRS}
    open(os.path.join(A.EVID, 'C_cave_xref.json'), 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))
    open(os.path.join(A.EVID, 'C_cave_xref.md'), 'w', encoding='utf-8').write(buf.getvalue())
    print(buf.getvalue())


if __name__ == '__main__':
    main()
