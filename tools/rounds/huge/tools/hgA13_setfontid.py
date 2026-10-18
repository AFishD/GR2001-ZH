# -*- coding: utf-8 -*-
r"""hgA13_setfontid.py — 只读: xref `IkeBaseButton::SetFontID(int)`(0x21D760) 与
`RSTextComponent` 的字体 id 来源，判定是否存在把 6/7(=huge) 传进去的静态证据。

产出: work/builds/GR_HUGE/evidence/hgA13_setfontid.txt
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

TGT = {0x21D760: 'IkeBaseButton::SetFontID(int)'}


def main():
    lines = []
    W = lines.append
    for tag in ('ZH113b',):
        e, f = H.A.load_elf(tag)
        blob = e.b
        hits = []
        for p in e.phdrs:
            if p['type'] != 1:
                continue
            for a in range(p['vaddr'], p['vaddr'] + p['filesz'], 4):
                o = a - H.VA2FILE
                if o < 0 or o + 4 > len(blob):
                    continue
                w = struct.unpack_from('<I', blob, o)[0]
                if (w >> 26) in (2, 3) and ((w & 0x3FFFFFF) << 2) in TGT:
                    hits.append(a)
        W('--- SetFontID(0x21D760) 引用 %d ---' % len(hits))
        for a in hits:
            s = e.sym_at(a)
            W('=' * 90)
            W('@%08X  in %s+0x%X' % (a, s['name'], a - s['value']))
            for (b, w, t) in H.dis_range(blob, a - 12 * 4, 18, H.VA2FILE):
                W('   %08X  %08X  %-32s%s' % (b, w if w is not None else 0, t,
                                              ' <<<' if b == a else ''))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA13_setfontid.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA13_setfontid.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
