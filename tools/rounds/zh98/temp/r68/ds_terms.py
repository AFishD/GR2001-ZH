# -*- coding: utf-8 -*-
"""Search for the Desert Siege campaign naming across the user's translation columns."""
import csv, io, os, re, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
D = os.path.join(ROOT, r"work\builds\GR_ZH111\text")
PAT = re.compile(u'围剿|围攻|沙漠风暴|荒漠|Desert Siege|DS ')
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\ds_terms.txt")
lines = []


def add(s):
    lines.append(s)
    print(s)


for fn in sorted(os.listdir(D)):
    if not fn.endswith('.csv') or '_view_' in fn:
        continue
    p = os.path.join(D, fn)
    with io.open(p, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for c in ('text_zh', 'text_edited', 'text_en'):
            v = r.get(c) or ''
            for m in PAT.finditer(v):
                a = max(0, m.start() - 40)
                b = min(len(v), m.end() + 40)
                add("%-30s %-13s %-11s %-12s %r"
                    % (fn, r.get('id', ''), c, r.get('kind', ''),
                       v[a:b].replace('\n', '\\n')))
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('\n'.join(lines) + '\n')
