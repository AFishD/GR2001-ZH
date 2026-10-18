import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = os.path.abspath(".")
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
sys.path.insert(0, os.path.join(REPO, "tools", "text_csv"))
import repack_font
man = repack_font.make_reencode_tables(
    os.path.join(REPO, "work", "builds", "GR_ZH94", "text"),
    os.path.join(REPO, "work", "builds", "GR_ZH94", "temp", "r46", "reencode_test"))
print("rows=%d edited=%d files=%d" % (man["rows"], man["edited_nonempty"], len(man["files"])))
