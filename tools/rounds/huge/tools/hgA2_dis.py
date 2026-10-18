# -*- coding: utf-8 -*-
r"""hgA2_dis.py — 只读: 反汇编 RSFont/RSFontMgr 面选择链上的全部函数 (EN 与 ZH 并排)。

产出: work/builds/GR_HUGE/evidence/hgA2_dis.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# (名称, VA, 指令数)  —— 指令数按 size/4 上取整, 由符号表 size 决定 (见 hgA1_syms.txt)
FUNCS = [
    ('RSFontMgr::ReadResourceFile',        0x219380, None),
    ('RSFont::operator=',                  0x219890, None),
    ('RSFontMgr::DrawString(3rd overload)', 0x219A70, None),
    ('RSFontMgr::DrawString(2)',           0x219E00, None),
    ('RSFontMgr::DrawString(1)',           0x219EB0, None),
    ('RSFontMgr::BeginFrame',              0x219F00, None),
    ('RSFontMgr::AddOneWord',              0x219F50, None),
    ('RSFontMgr::Flush',                   0x21A190, None),
    ('RSFontMgr::Draw',                    0x21A290, None),
    ('RSFontMgr::Reset',                   0x21A360, None),
    ('RSFontMgr::ReallocateSize',          0x21A3B0, None),
    ('RSFontMgr::Initialize',              0x21A450, None),
    ('RSFontMgr::~RSFontMgr',              0x21A470, None),
    ('RSFontMgr::Create',                  0x21A5B0, None),
    ('RSArray<RSFont>::__ct',              0x21A920, None),
    ('RSArray<RSFont>::~',                 0x21A930, None),
    ('RSArray<RSFont>::IncreaseToSize',    0x21A9A0, None),
    ('RSFont::ReadResource',               0x21AB50, None),
    ('RSFont::StringWidth',                0x21AC00, None),
    ('RSFont::CharHeight',                 0x21ACD0, None),
    ('RSFont::CharWidth',                  0x21AD10, None),
    ('RSFont::ComputeCharTextureCoords',   0x21ADE0, None),
    ('RSFont::~RSFont',                    0x21AF30, None),
    ('RSFont::RSFont',                     0x21AFA0, None),
    ('RSFontMgr::GetFont(int)',            0x3A17D0, None),
    ('RSFontMgr::Get()',                   0x3A17E0, None),
    ('RSArray<RSFont>::__vc',              0x2007E0, None),
]


def main():
    lines = []
    W = lines.append
    elfs = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        elfs[tag] = e
    for (nm, va, _n) in FUNCS:
        W('=' * 110)
        W('### %s  @ VA 0x%X' % (nm, va))
        for tag in ('EN_ORIG', 'ZH113b'):
            e = elfs[tag]
            s = None
            for q in e.syms:
                if q['value'] == va and q['size']:
                    s = q
                    break
            cnt = (s['size'] // 4) if s else 64
            if cnt == 0:
                cnt = 1
            W('--- %s  (%s size=%s) ---' % (tag, s['name'] if s else '?',
                                            s['size'] if s else '?'))
            for (a, w, t) in H.dis_range(e.b, va, cnt, H.VA2FILE):
                W('  %08X  %08X  %s' % (a, w if w is not None else 0, t))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA2_dis.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA2_dis.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
