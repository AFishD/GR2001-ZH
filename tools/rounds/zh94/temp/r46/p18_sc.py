import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "tools/text_csv")
import tcslib
cs = tcslib.Charset()
ok, det = tcslib.selfcheck_charset(cs)
print("ok =", ok)
for ln in det:
    if ln.startswith("[!!]"):
        print("  ", ln)
print("--- 的/你 当前码位:", cs.enc_pair.get("的"), cs.enc_pair.get("你"))
