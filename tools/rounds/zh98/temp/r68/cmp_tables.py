# -*- coding: utf-8 -*-
"""Compare the two title tables (GR_ZH110 standard vs GR_ZH111 actual base)."""
import csv, io, os

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
A = os.path.join(ROOT, r"work\builds\GR_ZH110\text\GR_ZH110_text_sf_titles.csv")
B = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r68\GR_ZH111_base_text_sf_titles.csv")
C = os.path.join(ROOT, r"work\builds\GR_ZH98\temp\r63\inject_titles\GR_ZH110_text_sf_titles.csv")


def load(p):
    with io.open(p, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


a, b, c = load(A), load(B), load(C)
print("A=%d B=%d C=%d" % (len(a), len(b), len(c)))
print("%-13s %-24s %-24s %-24s %-24s" % ("id", "A(G110 std dict)", "B(G111 disc)", "C(r63 demo)", "A.len/max"))
nd = 0
for ra, rb, rc in zip(a, b, c):
    assert ra["id"] == rb["id"] == rc["id"], (ra["id"], rb["id"], rc["id"])
    if not (ra["text_zh"] == rb["text_zh"] == ra["text_edited"] == rc["text_zh"]):
        nd += 1
        print("%-13s %-24s %-24s %-24s %-24s" % (ra["id"], ra["text_zh"], rb["text_zh"],
                                                 rc["text_zh"], ra["text_edited"]))
print("differing rows:", nd)
# also: which rows in A have text_edited != text_zh
print("\nA rows with text_edited != text_zh:")
for ra in a:
    if ra["text_edited"] != ra["text_zh"]:
        print("  ", ra["id"], repr(ra["text_zh"]), "->", repr(ra["text_edited"]))
print("B rows with text_edited != text_zh:")
for rb in b:
    if rb["text_edited"] != rb["text_zh"]:
        print("  ", rb["id"], repr(rb["text_zh"]), "->", repr(rb["text_edited"]))
print("\nB max_bytes for A0056:", [r["max_bytes"] for r in b if r["id"] == "SFXML:A0056"])
print("B offsets equal A offsets:",
      all(x["offset"] == y["offset"] and x["len_bytes"] == y["len_bytes"] for x, y in zip(a, b)))
