import os,sys,struct,subprocess
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
sys.path.insert(0, r"tools/text_csv")
import tcslib
HERE=r"work/builds/GR_ZH93/temp/r42"
iso = tcslib.Iso(r"work/builds/GR_ZH93/GR_ZH93.iso")
b = iso.read(295*2048, 0x4DED80)
iso.close()
open(os.path.join(HERE,"zh93_slus.bin"),"wb").write(b)
print("extracted", len(b))
