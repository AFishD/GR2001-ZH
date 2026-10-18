import csv, io, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
targets = ("影片","设定图","音乐","武器","奖章","背景","屏幕截图","访谈","预告片")
d = "work/builds/GR_ZH95/text"
for fn in sorted(os.listdir(d)):
    if not fn.endswith(".csv") or "_view_" in fn: continue
    for r in csv.DictReader(io.open(os.path.join(d,fn), encoding="utf-8-sig", newline="")):
        t = (r.get("text_edited") or "").strip()
        if t in targets:
            print("%-14s %-12s kind=%-8s entry=%-8s len=%-5s max=%s | %s" % (
                fn.replace("GR_ZH95_text_","").replace(".csv",""), r.get("id"), r.get("kind"),
                r.get("entry_index"), r.get("len_bytes"), r.get("max_bytes"), t))
