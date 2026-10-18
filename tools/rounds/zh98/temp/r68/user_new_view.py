# -*- coding: utf-8 -*-
"""Compact view: USER_NEW text_edited (line-broken) for the SF long rows we care about."""
import csv, io, os, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
BK = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")
LV = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\user_new_view.txt")

RANGE = sys.argv[1:] or ['0010-0049']


def lo(r):
    with io.open(r, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


bk = dict((r["id"], r) for r in lo(BK))
lv = dict((r["id"], r)) if False else dict((r["id"], r) for r in lo(LV))

want = set()
for spec in RANGE:
    a, b = spec.split('-')
    for n in range(int(a), int(b) + 1):
        want.add('SFXML:T%04d' % n)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for rid in sorted(want):
        b = bk.get(rid)
        l = lv.get(rid)
        if b is None and l is None:
            continue
        f.write(u"===== %s =====\n" % rid)
        f.write(u"--- EN: %s\n" % (b or l).get("text_en", ""))
        f.write(u"--- USER_NEW:\n%s\n" % (b or {}).get("text_edited", "").replace("{Warp}", "\n").replace("{WRAP}", "\n"))
        f.write(u"--- DISC:\n%s\n\n" % (l or {}).get("text_zh", ""))
print("wrote", OUT)
