# r74_phantom.py - READ-ONLY. Is 0x4154536F text from a specific scene resource?
#   * locate <=40-byte printable runs containing "ATSo"/"oSTA"/"STAo"/"STAt" anywhere
#     in the EE RAM dump, the ELF and both ISOs
#   * decompose the value as two 16-bit halves and check endianness both ways
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
SCENE = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r74",
                     "dump_r74_zh111_cycle", "reclut_f00000785_eeram.bin")
ZH_ELF = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r72", "SLUS_206.13.elf")
ISO_ZH = os.path.join(REPO, "work", "builds", "GR_ZH111", "GR_ZH111.iso")
ISO_EN = os.path.join(REPO, "work", "builds", "GR_EN_ORIG", "GR_EN_ORIG.iso")

FRAGS = [b"ATSo", b"oSTA", b"STAo", b"STAt", b"oSTAt"]


def printable_runs(blob, lo, hi, minlen=6, maxlen=64):
    """yield (start, text) of printable runs inside blob[lo:hi]"""
    cur = bytearray()
    start = 0
    for i in range(lo, hi):
        c = blob[i]
        if 32 <= c < 127:
            if not cur:
                start = i
            cur.append(c)
            if len(cur) > maxlen:
                yield (start, cur[:maxlen].decode("ascii"))
                cur = bytearray()
        else:
            if len(cur) >= minlen:
                yield (start, cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        yield (start, cur.decode("ascii"))


def analyse(name, blob):
    print("=" * 78)
    print("### %s  (%d bytes)" % (name, len(blob)))
    for f in FRAGS:
        hits = []
        s = 0
        while True:
            i = blob.find(f, s)
            if i < 0:
                break
            hits.append(i)
            s = i + 1
            if len(hits) >= 20:
                break
        if hits:
            print("  fragment %-6s -> %d hits" % (f.decode(), len(hits)))
            for h in hits[:6]:
                # reconstruct the enclosing printable run
                lo = max(0, h - 40)
                hi = min(len(blob), h + 48)
                txt = None
                for st, t in printable_runs(blob, lo, hi, minlen=4):
                    if st <= h < st + len(t) or abs(st - h) < 40:
                        txt = (st, t)
                        break
                print("     @0x%08X  run@0x%08X = %r" % (h, txt[0] if txt else -1,
                                                         txt[1] if txt else "?"))
    # exact value decomposition
    v = 0x4154536F
    print("  value 0x%08X:" % v)
    print("     LE bytes %s   BE bytes %s" % (
        " ".join("%02x" % c for c in struct.pack("<I", v)),
        " ".join("%02x" % c for c in struct.pack(">I", v))))
    print("     as 2x u16 LE: 0x%04X 0x%04X   as 2x u16 BE: 0x%04X 0x%04X" % (
        v & 0xFFFF, v >> 16, v >> 16, v & 0xFFFF))


def main():
    scene = open(SCENE, "rb").read()
    analyse("crash-scene EE RAM (frame 785)", scene)
    if os.path.exists(ZH_ELF):
        analyse("Chinese ELF", open(ZH_ELF, "rb").read())
    for p, n in ((ISO_ZH, "GR_ZH111.iso"), (ISO_EN, "GR_EN_ORIG.iso")):
        if os.path.exists(p):
            analyse(n, open(p, "rb").read())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
