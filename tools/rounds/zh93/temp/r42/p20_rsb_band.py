import os,sys,struct
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
sys.path.insert(0, r"tools/text_csv")
import tcslib
from PIL import Image
HERE=r"work/builds/GR_ZH93/temp/r42"
iso = tcslib.Iso(r"work/builds/GR_EN_ORIG/GR_EN_ORIG.iso")
e = iso.img_entry(tcslib.GR_LBA, 861)
rsb = iso.read(e["iso_off"], e["stored"])
pak_e=None
for i in range(24):
    x=iso.img_entry(tcslib.MENU_LBA,i)
    if x["name"]=="COMMON.PAK": pak_e=x; break
pak = iso.read(pak_e["iso_off"], pak_e["stored"])
iso.close()
pay = rsb[93:]
A = Image.new("RGB",(256,256))
ap = A.load()
for y in range(256):
    for x in range(256):
        o=(y*256+x)*4
        ap[x,y]=(pay[o],pay[o+1],pay[o+2])
A.resize((768,768), Image.NEAREST).save(os.path.join(HERE,"rsb_B_3x.png"))
# 图标区带 (y=170..225, x=0..140) 放大 8 倍
A.crop((0,170,140,226)).resize((140*8,56*8), Image.NEAREST).save(os.path.join(HERE,"rsb_B_band.png"))
print("ok")
