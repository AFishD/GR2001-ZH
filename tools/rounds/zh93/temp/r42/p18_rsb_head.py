import os,sys,struct
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
sys.path.insert(0, r"tools/text_csv")
import tcslib
iso = tcslib.Iso(r"work/builds/GR_EN_ORIG/GR_EN_ORIG.iso")
e = iso.img_entry(tcslib.GR_LBA, 861)
print("GR.IMG #861", e["name"], "stored", e["stored"], "real", e["real"], "off", hex(e["off"]))
b = iso.read(e["iso_off"], e["stored"])
iso.close()
print("size", len(b))
print("head hex:", b[:0x60].hex(" "))
for i in range(0, 0x60, 16):
    print("  %04X  %s  |%s|" % (i, b[i:i+16].hex(" "), "".join(chr(c) if 32<=c<127 else "." for c in b[i:i+16])))
