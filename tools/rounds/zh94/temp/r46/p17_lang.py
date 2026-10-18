import csv, io, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for ver in ("GR_ZH94", "GR_ZH95"):
    d = os.path.join("work","builds",ver,"text")
    if not os.path.isdir(d):
        print("== %s: no text dir" % ver); continue
    print("== %s ==" % ver)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".csv") or "_view_" in fn: continue
        for r in csv.DictReader(io.open(os.path.join(d,fn), encoding="utf-8-sig", newline="")):
            if r.get("id","").endswith("G058.I195") or (r.get("id","")=="LANG:G058.I195"):
                print("  %s | %s" % (fn, {k:(v[:70] if isinstance(v,str) else v) for k,v in r.items() if k in ("id","resource","container","entry_index","offset","len_bytes","kind","text_zh","text_edited")}))
