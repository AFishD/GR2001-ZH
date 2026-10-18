# -*- coding: utf-8 -*-
"""r76_mcdiff.py - compare two GR campaign saves (memcard files) field by field.

Read-only.  Reports the differing regions, plus a scan for values that look like
bogus pointers (outside 0x00000000-0x02000000) or bare small integers sitting in
word-aligned slots, which is the corruption signature of the live crash.
"""
import os
import struct
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mc")


def load(p):
    with open(p, "rb") as f:
        return f.read()


def hexwin(b, off, n=32):
    s = b[off:off + n]
    return " ".join("%02X" % c for c in s)


def asciiwin(b, off, n=32):
    s = b[off:off + n]
    return "".join(chr(c) if 32 <= c < 127 else "." for c in s)


def main():
    a_p = os.path.join(BASE, "zh", "BASLUS-20613GHOST001_7040.bin")
    b_p = os.path.join(BASE, "en", "BASLUS-20613GHOST001_7040.bin")
    a = load(a_p)   # written by the localized (GR_ZH111) session
    b = load(b_p)   # written by the clean English (GR_EN_ORIG) session
    print("A (zh) %s  %d B" % (a_p, len(a)))
    print("B (en) %s  %d B" % (b_p, len(b)))
    n = min(len(a), len(b))
    diff = [i for i in range(n) if a[i] != b[i]]
    print("diff bytes: %d / %d (%.2f%%)" % (len(diff), n, 100.0 * len(diff) / n))
    if not diff:
        return
    # coalesce
    ranges = []
    s = diff[0]
    p = diff[0]
    for i in diff[1:]:
        if i - p > 16:
            ranges.append((s, p))
            s = i
        p = i
    ranges.append((s, p))
    print("diff ranges (gap>16B): %d" % len(ranges))
    print("%-10s %-10s %-6s  %s" % ("start", "end", "len", "side"))
    for (s, e) in ranges[:80]:
        print("0x%06X  0x%06X  %-6d" % (s, e, e - s + 1))
    print()
    print("=== first 24 ranges, 32-byte windows ===")
    for (s, e) in ranges[:24]:
        st = max(0, s - 8)
        print("--- 0x%06X..0x%06X ---" % (s, e))
        print("  zh: %s  |%s|" % (hexwin(a, st), asciiwin(a, st)))
        print("  en: %s  |%s|" % (hexwin(b, st), asciiwin(b, st)))
    # suspicious word scan
    print()
    for tag, buf in (("zh", a), ("en", b)):
        bad = []
        small = 0
        for off in range(0, len(buf) - 4, 4):
            v = struct.unpack_from("<I", buf, off)[0]
            if 0x02000000 <= v < 0x10000000 and v != 0xFFFFFFFF:
                bad.append((off, v))
            if v in (0x10, 0x14, 0x18, 0x1C, 0x20):
                small += 1
        print("%s: words in [0x02000000,0x10000000) = %d ; words in {0x10,0x14,0x18,0x1C,0x20} = %d"
              % (tag, len(bad), small))
        for (off, v) in bad[:10]:
            print("    off 0x%06X = 0x%08X" % (off, v))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
