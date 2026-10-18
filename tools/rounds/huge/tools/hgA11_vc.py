# -*- coding: utf-8 -*-
r"""hgA11_vc.py — 只读: 找 `RSArray<RSFont>::__vc`(0x2007E0) 的调用点 + 内联展开，
用来发现"绕过 RSFontMgr::GetFont 直接取 fonts[i]"的地方。

产出: work/builds/GR_HUGE/evidence/hgA11_vc.txt
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 内联 __vc 的尾序列 (i*44): sll v1,a1,2 ; addu v1,v1,a1 ; sll v1,v1,1 ; addu v1,v1,a1 ; sll v1,v1,2
TAIL = [0x00051880, 0x00651821, 0x00031840, 0x00651821, 0x00031880]


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        blob = e.b
        W('=' * 100)
        W('%s' % tag)
        hits = []
        for p in e.phdrs:
            if p['type'] != 1:
                continue
            for a in range(p['vaddr'], p['vaddr'] + p['filesz'], 4):
                o = a - H.VA2FILE
                if o < 0 or o + 4 > len(blob):
                    continue
                w = struct.unpack_from('<I', blob, o)[0]
                if (w >> 26) in (2, 3) and ((w & 0x3FFFFFF) << 2) == 0x2007E0:
                    hits.append((a, 'jal/j 0x2007E0', w))
        W('--- jal/j 0x2007E0 (__vc<RSFont>) 命中 %d ---' % len(hits))
        for (a, t, w) in hits:
            s = e.sym_at(a)
            W('   %08X  %-16s  %s' % (a, t, ('%s+0x%X' % (s['name'], a - s['value'])) if s else '?'))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA11_vc.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
