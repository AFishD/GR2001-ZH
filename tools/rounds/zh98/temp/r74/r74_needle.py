# r74_needle.py - READ-ONLY. Exact needle search with raw-hex context dump (no text mangling).
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402


def dump(b, off, back=48, fwd=96, width=16):
    lo = max(0, off - back)
    hi = min(len(b), off + fwd)
    for r in range(lo, hi, width):
        row = b[r:r + width]
        hx = " ".join("%02x" % c for c in row)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        mark = " <== HIT" if r <= off < r + width else ""
        print("      %08x  %-47s |%s|%s" % (r, hx, asc, mark))


def main():
    p2s = sys.argv[1]
    entry = sys.argv[2]
    pats = [bytes.fromhex(x) for x in sys.argv[3:]]
    b = R.read_entry(p2s, entry)
    print("file=%s entry=%s len=%d (0x%x)" % (os.path.basename(p2s), entry, len(b), len(b)))
    for pat in pats:
        print("")
        print("### needle %s" % pat.hex(" "))
        s = 0
        n = 0
        while True:
            i = b.find(pat, s)
            if i < 0:
                break
            n += 1
            print("  --- hit #%d @ 0x%07x ---" % (n, i))
            dump(b, i)
            s = i + 1
            if n >= 6:
                print("  (capped at 6)")
                break
        print("  total=%d" % n)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
