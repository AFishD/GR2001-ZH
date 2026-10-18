# r74_scan2.py - READ-ONLY. Big scan: look for the bogus value 0x4154536F in many
# byte alignments / widths across EE RAM, IOP RAM, scratchpad of one or more p2s files.
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402

V = 0x4154536F
# every byte alignment of the 4-byte value, plus 4-byte-swapped and 64-bit forms
PATS = {}
for sh in range(0, 32, 8):
    PATS["LE<<%d" % sh] = ((V << sh) & 0xFFFFFFFF).to_bytes(4, "little")
    PATS["BE<<%d" % sh] = ((V << sh) & 0xFFFFFFFF).to_bytes(4, "big")
PATS["LE-64"] = (V).to_bytes(8, "little")
PATS["BE-64"] = (V).to_bytes(8, "big")

ENTRIES = ["eeMemory.bin", "iopMemory.bin", "Scratchpad.bin"]


def printable(seg):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in seg)


def scan_file(p2s):
    print("#" * 78)
    print("# FILE %s" % p2s)
    print("# mtime %s" % __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p2s)))
    print("#" * 78)
    for e in ENTRIES:
        try:
            blob = R.read_entry(p2s, e)
        except Exception as ex:
            print("  %-18s SKIP (%s)" % (e, ex))
            continue
        print("-- %-18s %d bytes" % (e, len(blob)))
        for name, pat in PATS.items():
            hits = []
            s = 0
            while True:
                i = blob.find(pat, s)
                if i < 0:
                    break
                hits.append(i)
                s = i + 1
                if len(hits) >= 8:
                    break
            if hits:
                print("     %-8s %s -> %d hits" % (name, pat.hex(" "), len(hits)))
                for h in hits[:4]:
                    lo = max(0, h - 56)
                    hi = min(len(blob), h + len(pat) + 56)
                    print("         @0x%07x |%s|" % (h, printable(blob[lo:hi])))
        # also the three ASCII fragments at every offset (already covered) plus
        # a raw dump of the 4 ASCII bytes in any order-of-interest
    print("")


def main():
    p2s_list = sys.argv[1:]
    for p in p2s_list:
        scan_file(p)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
