import hashlib, os, struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"tools/text_csv")
import tcslib
def grab(iso_p):
    iso = tcslib.Iso(iso_p)
    e = iso.img_entry(tcslib.GR_LBA, 861)
    rsb = iso.read(e["iso_off"], e["stored"])
    pak_e = None
    for i in range(24):
        x = iso.img_entry(tcslib.MENU_LBA, i)
        if x["name"] == "COMMON.PAK": pak_e = x; break
    pak = iso.read(pak_e["iso_off"], pak_e["stored"])
    iso.close()
    base=0; rec=None
    while base+8 <= len(pak):
        ty, nl = struct.unpack_from("<II", pak, base)
        if ty == 0x63 or nl > 64: break
        nm = pak[base+8:base+8+nl].decode("latin-1")
        q = base+8+nl
        psm,w,h,clut = struct.unpack_from("<4I", pak, q)
        pxoff = q+16+clut
        pxsz = struct.unpack_from("<I", pak, q+16+clut)[0]
        if nm == "pda_counterparts":
            rec = (nm,psm,w,h,clut,pak[pxoff+4:pxoff+4+pxsz][:65536], pak[q+16:q+16+16+1024])
            break
        base = pxoff+4+pxsz
    return e, rsb, rec
for tag, p in (("EN_ORIG", r"work/builds/GR_EN_ORIG/GR_EN_ORIG.iso"),
               ("GR_ZH93", r"work/builds/GR_ZH93/GR_ZH93.iso"),
               ("GR_ZH96_icon", r"work/builds/GR_ZH96_icon/GR_ZH96_icon.iso")):
    e, rsb, rec = grab(p)
    print("%-13s GR.IMG#861 %s stored=%d sha256=%s" % (tag, e["name"], e["stored"], hashlib.sha256(rsb).hexdigest()[:32]))
    print("              COMMON.PAK %s %dx%d psm=0x%02X 像素sha=%s CLUTsha=%s" % (rec[0], rec[2], rec[3], rec[1], hashlib.sha256(rec[5]).hexdigest()[:24], hashlib.sha256(rec[6]).hexdigest()[:24]))
