# -*- coding: utf-8 -*-
r"""hgA1_syms.py — 只读: 列出 ELF 符号里与 Font/String/Text/Style 相关的符号 + 面选择链候选。

产出: work/builds/GR_HUGE/evidence/hgA1_syms.txt
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PAT = re.compile(r'font|string|text|typog|style|glyph|char|letter|word', re.I)


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        W('=' * 100)
        W('%s  elf size=%d  syms=%d  phnum=%d  shnum=%d' % (tag, len(e.b), len(e.syms),
                                                            e.phnum, e.shnum))
        W(H.A.__dict__.get('_', '') and '' or '')
        W('--- PHDRS ---')
        W(e.report_phdrs())
        W('--- SHDIRS ---')
        W(e.report_shdrs())
        hits = [s for s in e.syms if s['name'] and PAT.search(s['name'])]
        W('--- 符号命中 %d ---' % len(hits))
        for s in sorted(hits, key=lambda x: x['value']):
            W('  0x%08X size=%-6d %-9s %s' % (s['value'], s['size'], s['typname'], s['name']))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA1_syms.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA1_syms.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
