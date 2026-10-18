import csv, io, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"work/builds/GR_ZH94/text/GR_ZH94_text_long.csv"
rows = list(csv.DictReader(io.open(p, encoding="utf-8-sig", newline="")))
print("cols:", list(rows[0].keys()))
print("rows:", len(rows))
for r in rows:
    if r.get("container","").find("SPECIAL") >= 0:
        print("%-16s entry=%-4s off=%-7s len=%-5s | %s" % (
            r.get("id"), r.get("entry_index"), r.get("offset"), r.get("len_bytes"),
            (r.get("text_edited") or "")[:56].replace("\n"," / ")))
