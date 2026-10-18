# -*- coding: utf-8 -*-
"""Dump the LANG rows whose EN contains 'DS ' / 'Desert' / 'campaign' plus their neighbours."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
P = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_short.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\menu_labels.txt")
with io.open(P, "r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
idx = {}
for n, r in enumerate(rows):
    idx[r["id"]] = n
keep = set()
for n, r in enumerate(rows):
    en = r.get("text_en") or ""
    if ("DS " in en) or ("Desert" in en) or ("campaign" in en.lower()) or ("Siege" in en):
        for d in range(-3, 4):
            if 0 <= n + d < len(rows):
                keep.add(n + d)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for n in sorted(keep):
        r = rows[n]
        f.write(u"%-16s EN=%-46r ZH=%-30r ED=%r\n"
                % (r["id"], r.get("text_en"), r.get("text_zh"), r.get("text_edited")))
print("wrote", OUT, len(keep))
