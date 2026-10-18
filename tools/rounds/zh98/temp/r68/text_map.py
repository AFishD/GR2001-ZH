# -*- coding: utf-8 -*-
"""Map every SFXML <text> (T####) to its first EN line / first DISC line, for title alignment."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
LV = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\text_map.txt")
with io.open(LV, "r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        en = (r.get("text_en") or "").replace("\n", " | ")
        zh = (r.get("text_zh") or "").replace("\n", " | ")
        f.write(u"%-13s EN[%3d]=%s\n%-13s ZH[%3d]=%s\n\n"
                % (r["id"], int(r["len_bytes"]), en[:120], "", len(zh), zh[:120]))
print("wrote", OUT, len(rows))
