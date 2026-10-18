# -*- coding: utf-8 -*-
"""Print the r63 checklist flags, and compute width estimates for every title."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
CK = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r63\GR_ZH110_sf_titles_checklist.csv")
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

with io.open(CK, "r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
print("# checklist rows", len(rows))
seen = set()
for r in rows:
    flag = r["flag"]
    key = flag.split(";")[0].strip()
    if r["id"] in seen:
        continue
    seen.add(r["id"])
    print("%-13s %-3s %-26s %-24s %s" % (r["id"], r["tag"], r["text_zh"], r["text_en"], flag[:110]))
