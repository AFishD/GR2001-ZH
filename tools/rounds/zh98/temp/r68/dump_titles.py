# -*- coding: utf-8 -*-
"""Dump the 145 SF titles into a compact readable text file for review."""
import csv, sys, io, os

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
SRC = os.path.join(ROOT, r"work\builds\GR_ZH110\text\GR_ZH110_text_sf_titles.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\titles_dump.txt")

rows = []
with io.open(SRC, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)

print("rows", len(rows))
print("cols", list(rows[0].keys()))

tags = {}
for row in rows:
    tags[row["tag"]] = tags.get(row["tag"], 0) + 1
print("tags", tags)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for i, row in enumerate(rows):
        f.write(u"%03d\t%s\t%s\tEN=[%s]\tZH=[%s]\tED=[%s]\toff=%s len=%s\n" % (
            i + 1, row["id"], row["tag"], row["text_en"], row["text_zh"],
            row["text_edited"], row["offset"], row["len_bytes"]))
print("wrote", OUT)
