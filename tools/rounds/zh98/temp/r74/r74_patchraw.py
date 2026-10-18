# r74_patchraw.py - READ-ONLY. Dump the raw rule region around the biggest patch
# cluster (0x00416E00..0x00417800) from the Chinese ELF, marking patched bytes,
# and try to read it as a C-string table.
import os
import re
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "rounds", "zh98", "temp", "r74"))
import r74_mips as M  # noqa: E402

DIFF = REPO + r"\work\builds\GR_ZH118\temp\elf_diff.txt"


def load_diff(path):
    out = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            m = re.match(r"^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2})$", ln)
            if m:
                out[int(m.group(1), 16)] = (int(m.group(2), 16), int(m.group(3), 16))
    return out


def main():
    lo = int(sys.argv[1], 16)
    hi = int(sys.argv[2], 16)
    zh = M.Elf(M.ELF)
    diffs = load_diff(DIFF)
    n_patched_in_range = sum(1 for va in diffs if lo <= va < hi)
    print("range 0x%08X..0x%08X   patched bytes in range = %d" % (lo, hi, n_patched_in_range))
    print("")

    # print rows of 16 bytes with patched bytes upper-cased and * marked
    for base in range(lo, hi, 16):
        row = zh.read_va(base, 16)
        if not row:
            break
        hx, asc = [], []
        for k, c in enumerate(row):
            va = base + k
            if va in diffs:
                hx.append(">%02X" % c)
                asc.append(chr(c) if 32 <= c < 127 else ".")
            else:
                hx.append(" %02X" % c)
                asc.append(chr(c) if 32 <= c < 127 else ".")
        print("  %08x %s |%s|" % (base, "".join(hx), "".join(asc)))

    # C-string table reading
    print("")
    print("=== C strings found in range (>=4 printable chars) ===")
    blob = zh.read_va(lo, hi - lo)
    cur = []
    start = 0
    for i, c in enumerate(blob):
        if 32 <= c < 127:
            if not cur:
                start = i
            cur.append(chr(c))
        else:
            if len(cur) >= 4:
                print("  0x%08X  %r" % (lo + start, "".join(cur)))
            cur = []
    if len(cur) >= 4:
        print("  0x%08X  %r" % (lo + start, "".join(cur)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
