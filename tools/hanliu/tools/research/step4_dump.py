# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
from res_encode import parse_expanded, build_expanded, esc

raw = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'rb').read()
gr = parse_expanded(raw)
ok = build_expanded(gr) == raw
print('round-trip parse->build == raw:', 'PASS' if ok else 'FAIL')

hdr1 = '# GR.IMG EN_STRINGS.RES full dump -- res_encode.py parse_expanded'
hdr2 = '# groups=%d entries=%d expanded=%d bytes (MENU: 66 groups 2232 entries 128545 bytes)' % (
    len(gr), sum(len(g.strings) for g in gr), len(raw))
hdr3 = '# format: G{gg}.I{iii} [len] = text (esc backslash-xNN for >0x7E)'
lines = [hdr1, hdr2, hdr3]
for gi, g in enumerate(gr, 1):
    for si, (s, attr) in enumerate(g.strings):
        lines.append('G%02d.I%03d [%d] %s' % (gi, si, len(s), esc(s)))
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'en_dump.txt'),'w',encoding='ascii',newline='\n').write('\n'.join(lines)+'\n')
print('en_dump.txt written: %d lines' % len(lines))

with open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'group_summary.txt'),'w',encoding='utf-8',newline='\n') as f:
    for gi, g in enumerate(gr, 1):
        tot = sum(len(s) for s,_ in g.strings)
        f.write('G%02d n=%-4d bytes=%-6d | %s\n' % (gi, len(g.strings), tot,
                ' || '.join(x[0][:60].decode('latin-1','replace').replace('\n',' ') for x in g.strings[:2])))
print('group_summary.txt written')
