# -*- coding: utf-8 -*-
"""Dump specific long rows from the LIVE (reduced) GR_ZH111 text table for inspection."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
SRC = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\live_long_dump.txt")
BKP = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")

with io.open(SRC, "r", encoding="utf-8-sig", newline="") as f:
    live = list(csv.DictReader(f))
with io.open(BKP, "r", encoding="utf-8-sig", newline="") as f:
    bk = list(csv.DictReader(f))

lb = dict((r["id"], r) for r in live)
bb = dict((r["id"], r) for r in bk)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for rid in sorted(set(lb) | set(bb)):
        a = (lb.get(rid, {}).get("text_zh") or "").replace("\n", "\\n")
        b = (bb.get(rid, {}).get("text_zh") or "").replace("\n", "\\n")
        f.write(u"===== %s =====\nLIVE: %s\nBACKUP: %s\n" % (rid, a, b))
print("wrote", OUT, "rows live", len(live), "backup", len(bk))
