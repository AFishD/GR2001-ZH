import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools/iso_build"); sys.path.insert(0, "tools/text_csv")
import tcslib, repack_font
sha = tcslib.sha256_file("work/builds/GR_ZH95/GR_ZH95.iso")
print("stamp GR_ZH95 ->", repack_font.stamp_charset("GR_ZH95", sha))
