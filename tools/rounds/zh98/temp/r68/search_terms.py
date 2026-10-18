# -*- coding: utf-8 -*-
"""Search the user's original SF long translation for terms (space/newline tolerant)."""
import csv, io, os, re, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
SRC = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")

with io.open(SRC, "r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))


def squash(s):
    return re.sub(r'[\s\u3000]+', '', s or '')


squashed = [(r["id"], squash(r["text_zh"]), squash(r["text_en"]), r["text_zh"]) for r in rows]

TERMS = sys.argv[1:] if len(sys.argv) > 1 else []
for t in TERMS:
    hits = []
    for (rid, zh, en, raw) in squashed:
        if t in zh:
            hits.append(rid)
    print(u"%-10s in ZH: %s" % (t, " ".join(hits) if hits else "(none)"))
print("---- total rows", len(rows))
