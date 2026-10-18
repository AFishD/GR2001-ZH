# r74_scan_multi.py - READ-ONLY. Search EE/IOP/scratchpad for several byte patterns
# and dump wide printable context around any hit.
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402

P2S = os.path.join(REPO, "work", "temp", "NEW_Mem", "SLUS-20613 (7A361FB5).01.p2s")

# patterns as ASCII-ish fragments; value 0x4154536F is "oSTA" on disk (LE)
PATS = [
    b"oSTA", b"STAr", b"STAs", b"oSTAt", b"RoSTA", b"STAN", b"STAG",
    b"START", b"STAT", b"STA", b"RoST", b"oST",
]
ENTRIES = ["eeMemory.bin", "iopMemory.bin", "Scratchpad.bin"]
WIDE = 80


def printable(seg):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in seg)


def main():
    blobs = {}
    for e in ENTRIES:
        try:
            blobs[e] = R.read_entry(P2S, e)
            print("%-18s %d bytes" % (e, len(blobs[e])))
        except Exception as ex:
            print("%-18s FAILED %s" % (e, ex))
    print("=" * 78)

    for pat in PATS:
        total = 0
        detail = []
        for e, blob in blobs.items():
            start = 0
            while True:
                i = blob.find(pat, start)
                if i < 0:
                    break
                total += 1
                if len(detail) < 14:
                    lo = max(0, i - WIDE)
                    hi = min(len(blob), i + len(pat) + WIDE)
                    detail.append((e, i, printable(blob[lo:hi])))
                start = i + 1
        print("")
        print("### pattern %-8s -> %d hits" % (pat.decode("ascii", "replace"), total))
        for e, i, ctx in detail:
            print("   %-16s @0x%07x  |%s|" % (e, i, ctx))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
