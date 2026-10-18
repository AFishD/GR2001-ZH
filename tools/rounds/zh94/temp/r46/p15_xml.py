import csv, io, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"work/builds/GR_ZH94/text/GR_ZH94_view_xml.csv"
rows = list(csv.DictReader(io.open(p, encoding="utf-8-sig", newline="")))
print("cols:", list(rows[0].keys()))
print("rows:", len(rows))
for r in rows[:6]:
    print({k: (v[:60] if isinstance(v, str) else v) for k, v in r.items()})
print("---- 含 T0011/T0018/T0031/T0034/T0037 的行 ----")
for r in rows:
    i = r.get("id","")
    if any(t in i for t in ("T0011","T0018","T0031","T0034","T0037")):
        print({k: (v[:80] if isinstance(v, str) else v) for k, v in r.items()})
