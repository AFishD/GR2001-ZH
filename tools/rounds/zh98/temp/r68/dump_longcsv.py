# -*- coding: utf-8 -*-
"""Dump the user's original translation (GR_ZH109 long csv) to plain text for grepping."""
import csv, io, os

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
SRC = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\user_zh_plain.txt")

with io.open(SRC, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)
    cols = r.fieldnames
    rows = list(r)
print("cols", cols)
print("rows", len(rows))
# which col holds zh
zhcol = "text_zh" if "text_zh" in cols else None
print("zhcol", zhcol)

kinds = {}
for row in rows:
    kinds[row.get("kind", "?")] = kinds.get(row.get("kind", "?"), 0) + 1
print("kinds", kinds)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for row in rows:
        zh = (row.get(zhcol) or "").replace(u"\r", u"").replace(u"\n", u"\\n")
        en = (row.get("text_en") or u"").replace(u"\r", u"").replace(u"\n", u"\\n")
        f.write(u"%s\t%s\t%s\tEN=%s\tZH=%s\n" % (row["id"], row.get("kind", ""),
                                                row.get("container", ""), en, zh))
print("wrote", OUT)
