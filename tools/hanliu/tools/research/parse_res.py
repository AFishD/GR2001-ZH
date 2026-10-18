# -*- coding: utf-8 -*-
"""Parse en_strings_res_expanded.bin (pure expanded EN_STRINGS.RES, per han_v2/RES_FORMAT.md)."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import json, struct, sys

def parse(path):
    d = open(path, 'rb').read()
    n_groups = struct.unpack_from('<I', d, 0)[0]
    off = 4
    groups = []
    for g in range(n_groups):
        sep = 0
        if g > 0:
            sep = struct.unpack_from('<I', d, off)[0]; off += 4
            for _ in range(sep):
                l = struct.unpack_from('<I', d, off)[0]; off += 4
                off += l          # extra string, no u16 tail
        cnt = struct.unpack_from('<I', d, off)[0]; off += 4
        entries = []
        for i in range(cnt):
            l = struct.unpack_from('<I', d, off)[0]; off += 4
            data = d[off:off+l]; off += l
            attr = struct.unpack_from('<H', d, off)[0]; off += 2
            entries.append({'i': i, 'len': l, 'attr': attr,
                            'bytes': data.hex(),
                            'text': ''.join(chr(b) for b in data)})
        groups.append({'sep': sep, 'count': cnt, 'entries': entries})
    return d, n_groups, groups, off, len(d)

if __name__ == '__main__':
    src = os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_res_expanded.bin')
    d, n, groups, off, total = parse(src)
    print('file bytes:', len(d), 'expected 128545')
    print('groups:', n, 'entries:', sum(g['count'] for g in groups))
    print('consumed:', off, 'terminator check:', d[off:off+8].hex(), 'file tail:', d[-8:].hex())
    print('counts:', [g['count'] for g in groups])
    # spot check against MANIFEST 1-indexed: groups[57] should be main_ui_pool(802), G58.I003 = 'Ok'
    g57 = groups[57]['entries']
    print('groups[57].count =', groups[57]['count'])
    print('groups[57].I003 =', repr(g57[3]['text']))
    print('groups[57].I091 =', repr(g57[91]['text']))
    print('groups[60].I001 =', repr(groups[60]['entries'][1]['text']))
    print('groups[64].I040 =', repr(groups[64]['entries'][40]['text']))
    json.dump({'n_groups': n, 'groups': groups}, open(os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand', 'res_parsed.json'), 'w', encoding='utf-8'))
    print('saved res_parsed.json')
