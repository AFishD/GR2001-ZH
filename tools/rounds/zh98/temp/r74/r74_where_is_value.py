# r74_where_is_value.py - READ-ONLY. Where does 0x4154536F ("oSTA") come from?
# Look in the ELF main segment, the symtab/strtab, and the whole ISO image.
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ZH_ELF = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r72", "SLUS_206.13.elf")
EN_ELF = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r74", "SLUS_206.13.EN.elf")
ZH_ISO = os.path.join(REPO, "work", "builds", "GR_ZH111", "GR_ZH111.iso")
EN_ISO = os.path.join(REPO, "work", "builds", "GR_EN_ORIG", "GR_EN_ORIG.iso")
SCENE = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r74",
                     "dump_r74_zh111_cycle", "reclut_f00000785_eeram.bin")

PATS = {
    "oSTA": b"oSTA",
    "ATSo": b"ATSo",
    "value LE": struct.pack("<I", 0x4154536F),
    "value BE": struct.pack(">I", 0x4154536F),
    "STA_ (ascii)": b"STA",
}


def scan(path, name, whole=True, limit=2 ** 31):
    if not os.path.exists(path):
        print("  %-28s MISSING" % name)
        return
    size = os.path.getsize(path)
    print("  %-28s %d bytes" % (name, size))
    with open(path, "rb") as f:
        data = f.read(min(size, limit))
    for pn, pat in PATS.items():
        hits = []
        s = 0
        while True:
            i = data.find(pat, s)
            if i < 0:
                break
            hits.append(i)
            s = i + 1
            if len(hits) >= 4000:
                break
        if pn.startswith("STA") or hits:
            print("      %-14s %5s hits%s" % (pn, len(hits),
                  "" if not hits else "  first: " + " ".join("0x%X" % h for h in hits[:8])))


def main():
    print("=== search for the phantom pointer value 0x4154536F ===")
    print("ELF (Chinese):")
    scan(ZH_ELF, "SLUS_206.13.elf (ZH)")
    print("ELF (English original, extracted):")
    scan(EN_ELF, "SLUS_206.13.EN.elf")
    print("crash-scene EE RAM:")
    scan(SCENE, "reclut_f785_eeram.bin")
    print("")
    print("=== ISO images (may be slow) ===")
    print("Chinese ISO:")
    scan(ZH_ISO, "GR_ZH111.iso")
    print("English ISO:")
    scan(EN_ISO, "GR_EN_ORIG.iso")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
