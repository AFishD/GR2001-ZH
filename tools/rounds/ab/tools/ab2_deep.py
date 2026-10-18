# -*- coding: utf-8 -*-
r"""ab2_deep.py — 深挖: 文字链函数的完整 EN/ZH 反汇编 + sp 偏移读写表 + 结构偏移表 (只读)

产出 evidence/_deep.txt (原始), 供人工整理成 A_offset_table.md / A_suspicious_offsets.md
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FUNCS = [
    ('strlwr', 0x407060, 0x4070B4),
    ('strupr', 0x408910, 0x408964),
    ('sceIpuInit_cave', 0x411690, 0x4116A8),
    ('DrawString', 0x219A70, 0x219DC0),
    ('AddOneWord', 0x219F50, 0x21A1A0),
    ('Flush', 0x21A1A0, 0x21A1E0),
    ('Draw', 0x21A2A0, 0x21A2E0),
    ('StringWidth', 0x21AC00, 0x21ACD0),
    ('CharWidth', 0x21AD10, 0x21ADD0),
    ('CharWidth_cave', 0x416F40, 0x417050),
    ('CompCharTC', 0x21ADE0, 0x21AE40),
    ('CompCharTC_cave', 0x417050, 0x417140),
    ('SetText_HTML', 0x21BD50, 0x21BDA0),
    ('ReadResource', 0x21BFE0, 0x21C070),
    ('DrawTheString', 0x21C4C0, 0x21C640),
    ('ComputeDrawXY', 0x21CA20, 0x21CC30),
    ('ComputeDrawXY_cave', 0x565730, 0x5657A0),
    ('DoWordWrap', 0x21CC10, 0x21CF00),
    ('DoWordWrap_cave', 0x417500, 0x4175D0),
    ('SetText_TC', 0x21CFC0, 0x21D020),
    ('DrawText_BaseButton', 0x21D830, 0x21D960),
    ('DrawText_BaseButton_cave', 0x565A00, 0x565A50),
    ('GetUISoldierAbbrev', 0x2ECDA0, 0x2ECF00),
    ('GetUISoldierAbbrev_cave', 0x56583C, 0x565910),
    ('GetActorNameAbbrev', 0x307090, 0x307140),
    ('GetActorNameAbbrev_cave', 0x5657C8, 0x565840),
    ('StringWidth_cave', 0x565670, 0x565730),
    ('DrawString_tramp', 0x565900, 0x565A00),
    ('sceRemove_cave', 0x416ED0, 0x417038),
    ('drawtext_ike', 0x1FF790, 0x1FF8E0),
    ('drawtext_keymap', 0x207160, 0x2071C0),
    ('DrawLetters', 0x2164E0, 0x2165C0),
    ('setlin', 0x519AC0, 0x519AE0),
]


def main():
    e_en, _ = A.load_elf('EN_ORIG')
    e_zh, _ = A.load_elf('ZH113b')
    out = []
    W = out.append
    W('ELF 映射: FILE = VA - 0x%X ; ISO = VA - 0x%X\n' % (A.VA2FILE, A.VA2ISO))
    for (nm, a, b) in FUNCS:
        W('\n' + '=' * 108)
        W('### %s   VA 0x%X..0x%X' % (nm, a, b))
        W('=' * 108)
        for (va, we, de) in A.dis_range(e_en.b, a, (b - a) // 4):
            wz = struct.unpack_from('<I', e_zh.b, va - A.VA2FILE)[0]
            dz = A.dis1(wz, va)
            mark = '  ' if we == wz else '★ '
            W('%s0x%08X  EN %08X %-36s | ZH %08X %s'
              % (mark, va, we, de, wz, dz if we != wz else ''))

    # ---- sp 偏移读写表 (DrawString) ----
    W('\n\n' + '#' * 108)
    W('# DrawString 栈帧偏移读写表 (sp-relative)')
    W('#' * 108)
    for tag, e in (('EN', e_en), ('ZH', e_zh)):
        rows = []
        for (va, ins, op, rt, imm, rs) in A.mem_ops(e.b, 0x219A70, 0x219DC0):
            if rs == 29:
                rows.append((va, ins, op, imm))
        W('\n-- %s: sp 访问 %d 条' % (tag, len(rows)))
        for (va, ins, op, imm) in rows:
            d = 'W' if op in A.STORES.values() else 'R'
            W('   0x%08X  %s  %-28s  sp%+d' % (va, d, ins, imm))

    # ---- 全 ELF: 所有 221/222/223(sp) 访问 ----
    W('\n\n' + '#' * 108)
    W('# 全 ELF 扫描: 立即数 = 221/222/223 且基址 = sp 的内存访问 (两盘)')
    W('#' * 108)
    ph = [p for p in e_zh.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
    for tag, e in (('EN', e_en), ('ZH', e_zh)):
        hits = []
        for o in range(ph['off'] & ~3, ph['off'] + ph['filesz'] - 3, 4):
            w = struct.unpack_from('<I', e.b, o)[0]
            op = w >> 26
            if op not in A.LOADS and op not in A.STORES:
                continue
            rs = (w >> 21) & 0x1F
            imm = (w & 0xFFFF) - 0x10000 if (w & 0x8000) else (w & 0xFFFF)
            if rs == 29 and imm in (221, 222, 223):
                va = e.off2va(o)[0]
                s = e.sym_at(va)
                hits.append((va, A.dis1(w, va), s['name'] if s else '?',
                             (va - s['value']) if s else 0))
        W('\n-- %s: %d 条' % (tag, len(hits)))
        for (va, ins, sn, dl) in hits:
            W('   0x%08X  %-30s  %s+0x%X' % (va, ins, sn, dl))

    # ---- ZH113b 全 ELF: 所有右移/左移字节常量与结构偏移 ----
    W('\n\n' + '#' * 108)
    W('# cave 代码里的「结构偏移」内存访问 (非 sp 基址) — 只列 ZH 新增/替换的指令')
    W('#' * 108)
    for (nm, a, b) in FUNCS:
        if not nm.endswith('_cave') and nm != 'DrawString_tramp':
            continue
        W('\n-- %s 0x%X..0x%X' % (nm, a, b))
        for (va, ins, op, rt, imm, rs) in A.mem_ops(e_zh.b, a, b):
            if rs == 29:
                continue
            W('   0x%08X  %-32s  base=%s off=%d/%+d'
              % (va, ins, A.R[rs], imm, imm))

    txt = '\n'.join(out)
    p = os.path.join(A.EVID, '_deep.txt')
    open(p, 'w', encoding='utf-8').write(txt)
    print('wrote', p, len(txt))
    # 只回显关键小节
    i = txt.find('# DrawString 栈帧偏移读写表')
    print(txt[i:i + 9000])


if __name__ == '__main__':
    main()
