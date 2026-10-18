# -*- coding: utf-8 -*-
"""Where do 荒漠围攻 / 沙漠风暴 appear in the GR_ZH111 text tables?"""
import csv, io, os, re, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
D = os.path.join(ROOT, r"work\builds\GR_ZH111\text")
PAT = re.compile(u'荒漠围攻|沙漠风暴|荒漠|围攻|沙漠|Desert')

for fn in sorted(os.listdir(D)):
    if not fn.endswith('.csv') or '_view_' in fn:
        continue
    p = os.path.join(D, fn)
    with io.open(p, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys()) if rows else []
    hits = 0
    for r in rows:
        for c in cols:
            v = r.get(c) or ''
            if isinstance(v, str) and PAT.search(v):
                hits += 1
                print("%-32s %-11s %-14s %-8s %r" % (fn, r.get('id', ''), c,
                                                     r.get('kind', ''), v[:150]))
    print("# %s -> %d hits" % (fn, hits))
