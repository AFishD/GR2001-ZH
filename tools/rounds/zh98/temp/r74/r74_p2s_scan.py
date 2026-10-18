# r74_p2s_scan.py - READ-ONLY. List entries of a PCSX2 .p2s savestate and search a
# decompressed RAM blob for a byte pattern, printing context.
#
# Usage:
#   python r74_p2s_scan.py list  <p2s>
#   python r74_p2s_scan.py scan  <p2s> <entry> <hexpattern> [before] [after]
#
# We import the repo's own reader (tools/iso_build/fix_zh116_p2s.py) so the zstd
# method-93 handling stays identical to the rest of the project.
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402
import zipfile  # noqa: E402


def do_list(p):
    with zipfile.ZipFile(p) as z:
        for i in z.infolist():
            print("%-34s method=%-3d comp=%-10d size=%d" % (
                i.filename, i.compress_type, i.compress_size, i.file_size))


def hexdump(b, base_off, width=16):
    for r in range(0, len(b), width):
        row = b[r:r + width]
        hx = " ".join("%02x" % c for c in row)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        print("  %08x  %-*s  |%s|" % (base_off + r, width * 3, hx, asc))


def do_scan(p, entry, pat, before, after):
    pat = bytes.fromhex(pat)
    print("entry    = %s" % entry)
    print("pattern  = %s (%d bytes)" % (pat.hex(" "), len(pat)))
    blob = R.read_entry(p, entry)
    print("blob len = %d (0x%x)" % (len(blob), len(blob)))
    hits = []
    start = 0
    while True:
        i = blob.find(pat, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
        if len(hits) > 500:
            print("  (truncated at 500 hits)")
            break
    print("hits     = %d" % len(hits))
    for k, off in enumerate(hits[:40]):
        lo = max(0, off - before)
        hi = min(len(blob), off + len(pat) + after)
        print("")
        print("--- hit #%d at blob offset 0x%x ---" % (k, off))
        hexdump(blob[lo:hi], lo)
        # printable reconstruction of the region
        seg = blob[lo:hi]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
        print("  ascii: %s" % txt)
    return blob, hits


def main():
    cmd = sys.argv[1]
    if cmd == "list":
        do_list(sys.argv[2])
    elif cmd == "scan":
        do_scan(sys.argv[2], sys.argv[3], sys.argv[4],
                int(sys.argv[5]) if len(sys.argv) > 5 else 64,
                int(sys.argv[6]) if len(sys.argv) > 6 else 96)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
