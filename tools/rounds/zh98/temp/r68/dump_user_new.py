# -*- coding: utf-8 -*-
"""Dump the user's OWN new translation (text_edited) for all SF long rows.

Two generations:
  BK  = work/builds/GR_ZH109/text_backup_before_wrapfix/GR_ZH109_text_long.csv
        (text_edited = 用户新译文, pre charset-reduction)
  LV  = work/builds/GR_ZH111/text/GR_ZH111_text_long.csv
        (text_zh = on-disc final, post reduction; == what the player reads)
"""
import csv, io, os, re, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
BK = os.path.join(ROOT, r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv")
LV = os.path.join(ROOT, r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv")
OUT = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\user_new_plain.txt")


def load(p):
    with io.open(p, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


bk, lv = load(BK), load(LV)
bkm = dict((r["id"], r) for r in bk)
lvm = dict((r["id"], r) for r in lv)


def one(s):
    return re.sub(r'[\s\u3000{}WARPwarp]+', '', s or '')


with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for rid in sorted(set(bkm) | set(lvm)):
        b = bkm.get(rid, {})
        l = lvm.get(rid, {})
        f.write(u"===== %s =====\nUSER_NEW(backup text_edited): %s\nDISC(live text_zh): %s\n"
                % (rid, (b.get("text_edited") or "").replace("\n", "\\n"),
                   (l.get("text_zh") or "").replace("\n", "\\n")))
print("wrote", OUT)

# ---- term search against text_edited ----
TERMS = sys.argv[1:]
if TERMS:
    sn_b = [(r["id"], one(r.get("text_edited"))) for r in bk]
    sn_l = [(r["id"], one(r.get("text_zh"))) for r in lv]
    for t in TERMS:
        hb = [rid for (rid, s) in sn_b if t in s]
        hl = [rid for (rid, s) in sn_l if t in s]
        print(u"%-12s USER_NEW:%-22s DISC:%s"
              % (t, " ".join(hb) if hb else "-", " ".join(hl) if hl else "-"))
