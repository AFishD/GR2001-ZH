# -*- coding: utf-8 -*-
"""Print the first ~6 lines of the USER_NEW + DISC text for T0065..T0069 (backstory/interview)."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
BK = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")
LV = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\t65_69.txt")


def lo(p):
    with io.open(p, "r", encoding="utf-8-sig", newline="") as f:
        return dict((r["id"], r) for r in csv.DictReader(f))


bk, lv = lo(BK), lo(LV)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for n in range(63, 70):
        rid = "SFXML:T%04d" % n
        b = bk.get(rid, {})
        l = lv.get(rid, {})
        f.write(u"===== %s  EN=%s\n" % (rid, (b.get("text_en") or "")[:110]))
        f.write(u"-- USER_NEW first 8 lines:\n")
        f.write(u"\n".join((b.get("text_edited") or "").replace("{Warp}", "\n")
                           .replace("{WRAP}", "\n").split("\n")[:8]) + "\n")
        f.write(u"-- DISC first 8 lines:\n")
        f.write(u"\n".join((l.get("text_zh") or "").split("\n")[:8]) + "\n\n")
print("wrote", OUT)
