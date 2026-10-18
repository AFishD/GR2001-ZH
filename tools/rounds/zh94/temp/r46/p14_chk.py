import json, io, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"tools/font_pipeline/data/charset_compiled_zh16.json"
j = json.load(io.open(p, encoding="utf-8"))
print("has _font_repack:", "_font_repack" in j)
print("pair count:", len(j["pair_of"]))
