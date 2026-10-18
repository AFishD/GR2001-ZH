# -*- coding: utf-8 -*-
r"""ab3_spframe.py — 每个文字链函数的栈帧访问 EN vs ZH 差异 (只读)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# (名字, 起, 止) —— 覆盖整函数
FUNCS = [
    ('DrawString', 0x219A70, 0x219DC0),
    ('AddOneWord', 0x219F50, 0x21A1A0),
    ('Flush', 0x21A1A0, 0x21A240),
    ('Draw', 0x21A2A0, 0x21A370),
    ('StringWidth', 0x21AC00, 0x21ACD0),
    ('CharWidth', 0x21AD10, 0x21ADF0),
    ('ComputeCharTextureCoords', 0x21ADE0, 0x21AF30),
    ('SetText_HTML', 0x21BD50, 0x21BDA0),
    ('ReadResource', 0x21BFE0, 0x21C100),
    ('DrawTheString', 0x21C4C0, 0x21C8C0),
    ('ComputeDrawXY', 0x21CA20, 0x21CC10),
    ('DoWordWrap', 0x21CC10, 0x21CFC0),
    ('SetText_TC', 0x21CFC0, 0x21D020),
    ('DrawText_BaseButton', 0x21D830, 0x21DA40),
    ('DrawText_IkeButton', 0x1FF790, 0x1FFAE0),
    ('DrawText_KeyMapButton', 0x207160, 0x207380),
    ('DrawLetters', 0x2164E0, 0x216600),
    ('GetUISoldierAbbrev', 0x2ECDA0, 0x2ECF60),
    ('GetActorNameAbbrev', 0x307090, 0x307160),
    ('DisplayMessages', 0x22DDA0, 0x22E300),
]


def main():
    e_en, _ = A.load_elf('EN_ORIG')
    e_zh, _ = A.load_elf('ZH113b')
    out = []
    W = out.append
    for (nm, a, b) in FUNCS:
        seen = {}
        for tag, e in (('EN', e_en), ('ZH', e_zh)):
            d = {}
            for (va, ins, op, rt, imm, rs) in A.mem_ops(e.b, a, b):
                if rs != 29:
                    continue
                d[va] = (imm, 'W' if op in A.STORES.values() else 'R', ins)
            seen[tag] = d
        # 按 VA 逐条比较 (能抓到"同一偏移、指令不同"的情形)
        allva = sorted(set(seen['EN']) | set(seen['ZH']))
        diffs = [v for v in allva if seen['EN'].get(v) != seen['ZH'].get(v)]
        W('\n' + '=' * 100)
        W('### %s  0x%X..0x%X   sp 访问 %d 条 (EN) / %d 条 (ZH)'
          % (nm, a, b, len(seen['EN']), len(seen['ZH'])))
        if not diffs:
            W('   EN/ZH 栈访问**逐条完全一致**')
        for v in diffs:
            W('  ★ 0x%08X' % v)
            for tag in ('EN', 'ZH'):
                x = seen[tag].get(v)
                W('       %s %s' % (tag, ('sp%+d %s %s' % x) if x else '(无此指令)'))
    txt = '\n'.join(out)
    open(os.path.join(A.EVID, '_spframe.txt'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
