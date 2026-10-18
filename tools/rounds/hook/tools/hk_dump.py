# -*- coding: utf-8 -*-
r"""hk_dump.py — 关键函数/钩子的 EN|ZH 全文反汇编 + 栈帧读写表 (只读既有盘)."""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

EN = H.elf('EN')
ZH = H.elf('ZH')

RANGES = [
    ('DrawString_epilogue', 0x219DC0, 0x219E60),
    ('DrawString_head', 0x219A70, 0x219AA0),
    ('DrawString_interceptor', 0x565930, 0x5659B0),
    ('GetActorNameAbbrev', 0x307090, 0x307140),
    ('GetActorNameAbbrev_cave', 0x5657C0, 0x565840),
    ('GetUISoldierAbbrev_cave', 0x56583C, 0x565910),
    ('Substring_541038_ctx', 0x541000, 0x541070),
    ('RSUIString_dtor', 0x541E90, 0x541ED0),
    ('RSUIString_assign', 0x541CA0, 0x541CF0),
    ('mmalloc_free_102764', 0x102740, 0x1027A0),
    ('small_free_102A30', 0x102A20, 0x102AD0),
    ('chunk_free_head', 0x101D00, 0x101D20),
    ('chunk_alloc_102220', 0x102210, 0x102240),
    ('chunk_alloc_1024E8', 0x1024E0, 0x102500),
    ('GetFireTeam_17C57C', 0x17C550, 0x17C5A0),
    ('GetBestAwareness_39A3C0', 0x39A380, 0x39A3E0),
    ('HumanDynColl_3CF414', 0x3CF3E0, 0x3CF440),
    ('__mi__RSVector3_114490', 0x114480, 0x1144B0),
    ('SetLinearSampling', 0x519AC0, 0x519AE0),
    ('sceRemove_cave_head', 0x416ED0, 0x417040),
    ('sceDclose_cave_SetText', 0x417640, 0x4176E8),
    ('DrawString_tramp_entry', 0x5658F0, 0x565930),
    ('DrawString_body_219E60', 0x219E60, 0x219F60),
    ('DrawTheString_21C5E0', 0x21C5E0, 0x21C650),
    ('s_Pool_helper_565760', 0x565660, 0x5657C8),
    ('ComputeDrawXY_cave', 0x565730, 0x5657A0),
    ('sceFormat_cave', 0x417150, 0x417250),
    ('sceDclose_cave_full', 0x417600, 0x4176E8),
    ('sceRemove_cave_full', 0x416ED0, 0x41703C),
]


def main():
    lines = []
    for (name, a, b) in RANGES:
        lines.append('=' * 110)
        lines.append('### %s   VA 0x%X..0x%X' % (name, a, b))
        lines.append('=' * 110)
        for i in range(0, (b - a) // 4):
            va = a + i * 4
            o = H.va2file(va)
            we = int.from_bytes(EN.b[o:o + 4], 'little')
            wz = int.from_bytes(ZH.b[o:o + 4], 'little')
            mark = '★' if we != wz else ' '
            lines.append('%s 0x%08X  EN %-34s | ZH %-34s'
                         % (mark, va, H.dis1(we, va), H.dis1(wz, va)))
        lines.append('')

    # 栈帧表 (全函数范围, 用符号 size)
    lines.append('=' * 110)
    lines.append('# 栈帧读写表 (按符号边界, EN vs ZH)')
    lines.append('=' * 110)
    for nm in ['DrawString__9RSFontMgrFPCcffRC7RSColorP6RSFontPCiPCii',
               'ComputeDrawXY__15RSTextComponentFRC10RSUIString',
               'DoWordWrap__15RSTextComponentFRC10RSUIString',
               'GetActorNameAbbreviated__9ActorFileCFv',
               'GetUISoldierAbbreviateName__Fii']:
        s = [x for x in EN.syms if x['name'] == nm]
        if not s:
            lines.append('!! 未找到符号 %s' % nm)
            continue
        s = s[0]
        a, b = s['value'], s['value'] + s['size']
        lines.append('')
        lines.append('## %s  VA 0x%X..0x%X (size %d)' % (nm.split('__')[0], a, b, s['size']))
        for tag, e in (('EN', EN), ('ZH', ZH)):
            acc = H.sp_accesses(e.b, a, b)
            lines.append('  -- %s: sp 访问 %d 条' % (tag, len(acc)))
            for (va, rw, txt, off) in acc:
                lines.append('     0x%08X  %s  %-30s %s' % (va, rw, txt, off))
        # fp 写入点
        for tag, e in (('EN', EN), ('ZH', ZH)):
            w = H.reg_writes(e.b, a, b, 30)     # $fp = $s8 = 30
            lines.append('  -- %s: 写 $fp 的指令 %d 条: %s'
                         % (tag, len(w), ', '.join('0x%X' % x[0] for x in w)))

    txt = '\n'.join(lines)
    out = os.path.join(H.EVID, 'hk_dump.txt')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(txt)
    print('wrote %s (%d chars, %d lines)' % (out, len(txt), txt.count('\n')))


if __name__ == '__main__':
    main()
