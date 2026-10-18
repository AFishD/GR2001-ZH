# -*- coding: utf-8 -*-
r"""p25_make_test_csv2.py -- 把测试文本放到 nav_sf6 实际到达的条目 (SFXML:T0063)"""
import csv, io, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "text_csv"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import tcslib

SRC = os.path.join(REPO, "work", "builds", "GR_ZH93", "text")
DST = os.path.join(HERE, "csv_in2")
TID = "SFXML:T0063"
BOX = "图"
TEST = "\n".join([
    "1={{BTN:E0B1}}" + BOX,
    "2={{BTN:E0B5}}" + BOX,
    "3={{BTN:E0E7}}" + BOX,
    "4={{BTN:E0F1}}" + BOX,
    "5={{BTN:E0B1}}{{BTN:E0B5}}" + BOX,
    "6={{BTN:E0E7}}{{BTN:E0F1}}" + BOX,
])
print("[测试文本]")
for ln in TEST.split("\n"):
    print("   %s" % ln)
cs = tcslib.Charset()
b = cs.encode_strict(cs.marks_to_pua(TEST.replace("\n", "{br}")))
print("[字节] %d B: %s" % (len(b), " ".join("%02X" % x for x in b)))
if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)
hit = 0
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith(".csv"):
        continue
    with io.open(os.path.join(SRC, fn), encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f); cols = rd.fieldnames; rows = list(rd)
    for r in rows:
        if r["id"] == TID:
            r["text_edited"] = TEST; hit += 1
    with io.open(os.path.join(DST, fn), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\r\n")
        w.writeheader(); w.writerows(rows)
    print("[写] %-32s %5d 行" % (fn, len(rows)))
for fn in os.listdir(SRC):
    if fn.endswith(".meta.json"):
        shutil.copy2(os.path.join(SRC, fn), os.path.join(DST, fn))
assert hit == 1, hit
print("[out] %s" % DST)
