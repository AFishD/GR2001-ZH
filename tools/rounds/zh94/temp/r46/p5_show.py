import json, io, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
j = json.load(io.open(r"work/builds/GR_ZH94/temp/r46/repack_dryrun.json", encoding="utf-8"))
for k in ("cross_check_dump_font","cells","glyphs","capacity","atlas"):
    print("== %s ==" % k)
    print(json.dumps(j[k], ensure_ascii=False, indent=1)[:1400])
