# -*- coding: utf-8 -*-
r"""hgA7_callsites.py — 只读: 对每条 DrawString/GetFont 调用点打印前后 ±14 条指令上下文，
用于读出"字体索引 / RSFont*"实参。

产出: work/builds/GR_HUGE/evidence/hgA7_callsites.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SITES = [
    # (标签, 调用点 VA)
    ('DrawString(2nd, int fontIdx)', 0x2B8B1C), ('DrawString(2nd, int fontIdx)', 0x2B8BE8),
    ('DrawString(2nd, int fontIdx)', 0x2B8CCC), ('DrawString(2nd, int fontIdx)', 0x2B8DB8),
    ('DrawString(2nd, int fontIdx)', 0x2B8EA8), ('DrawString(2nd, int fontIdx)', 0x2B8F8C),
    ('DrawString(2nd, int fontIdx)', 0x2B9070), ('DrawString(2nd, int fontIdx)', 0x2B9288),
    ('DrawString(2nd, int fontIdx)', 0x2B9358), ('DrawString(2nd, int fontIdx)', 0x2B9488),
    ('DrawString(2nd, int fontIdx)', 0x2B95B4), ('DrawString(2nd, int fontIdx)', 0x2B9680),
    ('DrawString(2nd, int fontIdx)', 0x2B974C), ('DrawString(2nd, int fontIdx)', 0x2B9874),
    ('DrawString(2nd, int fontIdx)', 0x2B999C), ('DrawString(2nd, int fontIdx)', 0x2B9CA0),
    ('DrawString(2nd, int fontIdx)', 0x2B9D70), ('DrawString(2nd, int fontIdx)', 0x2B9E60),
    ('DrawString(2nd, int fontIdx)', 0x2B9F38), ('DrawString(2nd, int fontIdx)', 0x2BA028),
    ('DrawString(2nd, int fontIdx)', 0x2C22B4),
    ('GetFont(int)', 0x3A14A4), ('GetFont(int)', 0x3A15BC), ('GetFont(int)', 0x3A19C4),
    ('GetFont(int)', 0x3A1A48), ('GetFont(int)', 0x3A1AC0), ('GetFont(int)', 0x3A1DD0),
    ('GetFont(int)', 0x3A1F74), ('GetFont(int)', 0x3DEFA4), ('GetFont(int)', 0x3DF09C),
    ('DrawString(1st, i, i, RSFont*)', 0x216588),
    ('DrawString(1st, i, i, RSFont*)', 0x21C56C),
    ('DrawString(1st, i, i, RSFont*)', 0x21C940),
    ('DrawString(1st, i, i, RSFont*)', 0x3A14CC),
    ('DrawString(1st, i, i, RSFont*)', 0x3A19EC),
    ('DrawString(1st, i, i, RSFont*)', 0x3A1DF8),
    ('DrawString(1st, i, i, RSFont*)', 0x3DEFD8),
    ('DrawString(3rd, ..., RSFont*)', 0x22E26C),
    ('DrawString(3rd, ..., RSFont*)', 0x23D6EC),
    ('DrawString(3rd, ..., RSFont*)', 0x2E851C),
    ('DrawString(3rd, ..., RSFont*)', 0x20C7C4),
    ('DrawString(3rd, ..., RSFont*)', 0x2DE708),
]


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        blob = e.b
        W('#' * 110)
        W('## %s' % tag)
        for (lbl, va) in SITES:
            s = e.sym_at(va)
            W('=' * 110)
            W('%s  @VA 0x%X   in %s+0x%X'
              % (lbl, va, s['name'] if s else '?', (va - s['value']) if s else 0))
            for (a, w, t) in H.dis_range(blob, va - 14 * 4, 29, H.VA2FILE):
                mark = ' <<<' if a == va else '    '
                W('   %08X  %08X  %-32s%s' % (a, w if w is not None else 0, t, mark))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA7_callsites.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA7_callsites.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
