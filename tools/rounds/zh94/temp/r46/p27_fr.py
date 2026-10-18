import json, io, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
j = json.load(io.open(r"tools/font_pipeline/data/charset_compiled_zh16.json", encoding="utf-8"))
fr = j.get("_font_repack") or {}
print("iso_sha256 recorded =", fr.get("iso_sha256"))
print("moved_last =", fr.get("moved_last"), " codes_changed_last =", fr.get("codes_changed_last"))
print("remaining =", fr.get("remaining_capacity"))
