# -*- coding: utf-8 -*-
"""Trace the evolution of SFXML:T0055 / T0051 etc. across the text generations."""
import csv, io, os, sys, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"

FILES = [
    ("backup_before_wrapfix", r"work\builds\GR_ZH109\text_backup_before_wrapfix\GR_ZH109_text_long.csv"),
    ("G109_live_long", r"work\builds\GR_ZH109\text\GR_ZH109_text_long.csv"),
    ("G109_live_tmp", r"work\builds\GR_ZH109\text\GR_ZH109_text_long.csv.rt.tmp"),
    ("r64_before_del_align", r"work\builds\GR_ZH98\temp\r64\before_del_align.csv"),
    ("G110_long", r"work\builds\GR_ZH110\text\GR_ZH110_text_long.csv"),
    ("G111_long", r"work\builds\GR_ZH111\text\GR_ZH111_text_long.csv"),
]

IDS = ["SFXML:T0055", "SFXML:T0051", "SFXML:T0052", "SFXML:T0053", "SFXML:T0057",
       "SFXML:T0059", "SFXML:T0043", "SFXML:T0010", "SFXML:T0032", "SFXML:T0012"]


def load(p):
    full = os.path.join(ROOT, p)
    if not os.path.isfile(full):
        return None, None, None
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(full)).isoformat(' ', 'seconds')
    with io.open(full, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f)), mt, os.path.getsize(full)


for name, p in FILES:
    rows, mt, size = load(p)
    if rows is None:
        print("== %-22s MISSING" % name)
        continue
    by = dict((r["id"], r) for r in rows)
    print("== %-22s %8d B  mtime=%s  cols=%s" % (name, size, mt,
                                                 ",".join(k for k in rows[0].keys())))
    for rid in IDS:
        r = by.get(rid)
        if r is None:
            continue
        zh = (r.get("text_zh") or "")[:26].replace("\n", "\\n")
        ed = (r.get("text_edited") or "")[:26].replace("\n", "\\n")
        mark = ""
        blob = (r.get("text_zh") or "") + (r.get("text_edited") or "")
        for probe in ("拉默雷斯", "拉米雷斯", "亨利", "汉利", "荣誉勋章", "国会最高勋章"):
            if probe in blob:
                mark += "[" + probe + "]"
        print("   %-12s zh=%-28r ed=%-28r %s" % (rid, zh, ed, mark))
