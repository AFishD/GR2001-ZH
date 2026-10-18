# r74_scan_dict.py - READ-ONLY. Broad reconstruction of the bogus pointer from the
# reproduced crash scene's RAM dump:
#   * what ASLR-free address space could 0x4154536F live in (EE RAM / IOP RAM / VRAM)
#   * its low-32 / high-32 halves interpreted as text
#   * the 64-bit 'BaseGameMap' window
#   * the crash-site words
import os
import struct
import sys

D = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r74\dump_r74_zh111_cycle"
EE = os.path.join(D, "reclut_f00000785_eeram.bin")
IOP = os.path.join(D, "reclut_f00000785_iopram.bin")

V = 0x4154536F


def printable(seg):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in seg)


def show(blob, name, off, back=32, fwd=64):
    lo = max(0, off - back)
    hi = min(len(blob), off + fwd)
    for r in range(lo, hi, 16):
        row = blob[r:r + 16]
        mark = " <== " if r <= off < r + 16 else "     "
        print("    %s %08x  %-47s |%s|" % (mark, r, " ".join("%02x" % c for c in row),
                                           printable(row)))


def main():
    ee = open(EE, "rb").read()
    iop = open(IOP, "rb").read()
    print("EE RAM  = %d bytes (0x%X)" % (len(ee), len(ee)))
    print("IOP RAM = %d bytes (0x%X)" % (len(iop), len(iop)))
    print("")

    print("=== where could VA 0x%08X live? ===" % V)
    cands = []
    if V < len(ee):
        cands.append(("EE main RAM", ee, V))
    if 0x1C000000 <= V < 0x1C000000 + len(iop):
        cands.append(("IOP RAM (0x1C000000 base)", iop, V - 0x1C000000))
    if 0x1F800000 <= V < 0x1F800000 + 1024:
        cands.append(("EE scratchpad", None, V - 0x1F800000))
    if not cands:
        print("   NO: 0x%08X is outside EE RAM / IOP RAM / scratchpad in this dump" % V)
    for n, b, o in cands:
        print("   %s @0x%X" % (n, o))
        show(b, n, o)
    print("")

    print("=== the crash-site words ===")
    for va in (0x0, 0x4, 0x8, 0xC, 0x10):
        if va + 16 <= len(ee):
            print("  EA 0x%02X:" % va)
            show(ee, "ea", va, back=0, fwd=48)
    print("")

    print("=== ASCII halves of 0x%08X ===" % V)
    print("   LE bytes: %s" % " ".join("%02x" % c for c in struct.pack("<I", V)))
    print("   as text (LE order): %r" % printable(struct.pack("<I", V)))
    print("   as text (BE order): %r" % printable(struct.pack(">I", V)))
    print("   high16=0x%04X -> text %r ; low16=0x%04X -> text %r" % (
        V >> 16, printable(struct.pack(">H", V >> 16)), V & 0xFFFF, printable(struct.pack(">H", V & 0xFFFF))))
    print("")

    print("=== search both blobs for the ASCII fragments ===")
    for pat in (b"oSTA", b"ATSo", b"STAr", b"STAs", b"STAt", b"STAN", b"STAG", b"STAR"):
        for nm, b in (("EE", ee), ("IOP", iop)):
            hits = []
            s = 0
            while True:
                i = b.find(pat, s)
                if i < 0:
                    break
                hits.append(i)
                s = i + 1
                if len(hits) > 60:
                    break
            if hits:
                print("  %-4s %-6s %3d hits  first: %s" % (
                    nm, pat.decode("ascii", "replace"), len(hits),
                    " ".join("0x%07x" % h for h in hits[:10])))
    print("")

    print("=== the 64-bit word at EA 8 (BaseGameMap) ===")
    w = struct.unpack_from("<Q", ee, 8)[0]
    print("   u64 @8 = 0x%016X" % w)
    print("   lo32 = 0x%08X  hi32 = 0x%08X" % (w & 0xFFFFFFFF, w >> 32))
    print("")

    print("=== does the string from the user's screenshot scene exist? (spot checks) ===")
    for s in (b"BASLUS-20613", b"BASLUS-20613GHOST002", b"oSTA", b"BaseGameMap"):
        print("   %-24s EE hits=%d IOP hits=%d" % (
            s.decode(), ee.count(s), iop.count(s)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
