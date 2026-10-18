# -*- coding: utf-8 -*-
r"""cave_audit.py -- round79 "cave count vs bytes" audit driver.

READ-ONLY.  Produces, under work/builds/GR_ZH98/temp/r79/dump/:

  diff_ranges.txt   every changed 4-byte word, coalesced, orig -> cur
  side_<lo>_<hi>.txt  side-by-side disassembly of a VA window (orig | cur)
  jmap.txt          every `j <cave>` / `jal <cave>` patch point and its cave body
  writes.txt        every store instruction inside the cave ranges (sb/sh/sw/sd)
                    with the source register's provenance, to test "count vs bytes"

usage:
  python cave_audit.py ranges
  python cave_audit.py side <loVA> <hiVA> [label]
  python cave_audit.py jmap
  python cave_audit.py writes
  python cave_audit.py xref <targetVA>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cave_dis import Elf, dis  # noqa: E402

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ORIG = os.path.join(REPO, r"third_party\orig\ps2\slus_out\SLUS_206.13")
CUR = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump\elf_zh113b.bin")
OUT = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump")

# every cave / patch region this audit cares about (current-ELF VAs)
CAVES = [
    (0x407078, 0x407098, "cave A  single-byte code fixup #1"),
    (0x408928, 0x408948, "cave A' single-byte code fixup #2"),
    (0x411690, 0x4116B0, "cave B  (j from 0x21CC08)"),
    (0x216ED0 - 0x100000 + 0x100000, 0x416ED0, "placeholder"),
]
CAVE_RANGES = [
    (0x416ED0, 0x41703C, "char decoder (j/jal target 0x416ED0)"),
    (0x416F40, 0x41703C, "CharWidth (j target 0x416F40)"),
    (0x417050, 0x41713C, "ComputeCharTextureCoords grid (j target 0x417050)"),
    (0x417150, 0x4171C8, "StringWidth inner loop (j target 0x417150)"),
    (0x417200, 0x41721C, "cctc tweak (j target 0x417200)"),
    (0x417500, 0x417600, "layout cave (j target 0x417500)"),
    (0x417600, 0x4176E8, "text metrics caves (0x417650/0x417680/0x4176A0/0x4176B0)"),
    (0x411690, 0x4116A8, "cave B (j target 0x411690)"),
    (0x407078, 0x407098, "cave A"),
    (0x408928, 0x408948, "cave A2"),
    (0x565670, 0x56571C, "StringWidth tail / SWKERN (j target 0x565670)"),
    (0x565730, 0x5657C8, "layout cave (j targets 0x565730/0x565760)"),
    (0x5657C8, 0x5658C0, "menu text cave (j target 0x5657C8)"),
    (0x565900, 0x5659A8, "draw wrapper (j target 0x565900)"),
    (0x565A00, 0x565A48, "centering cave (j target 0x565A00)"),
]


def ranges():
    do = Elf(ORIG)
    dc = Elf(CUR)
    va0, off_o, fs = do.text()
    _, off_c, _ = dc.text()
    assert do.read(va0, 0x40000) and off_o and off_c
    lines = []
    n = fs
    diffs = []
    for i in range(0, n, 4):
        a = do.d[off_o + i:off_o + i + 4]
        b = dc.d[off_c + i:off_c + i + 4]
        if a != b:
            diffs.append(i)
    lines.append("=== %d differing words over %d bytes ===" % (len(diffs), n))
    rs = []
    for i in diffs:
        if rs and i - rs[-1][1] <= 16:
            rs[-1][1] = i + 4
        else:
            rs.append([i, i + 4])
    lines.append("=== %d coalesced ranges (gap<=16B) ===" % len(rs))
    for (s, e) in rs:
        lines.append("\n--- VA 0x%08X..0x%08X (%d B)" % (va0 + s, va0 + e, e - s))
        for i in range(s, e, 4):
            a = struct.unpack("<I", do.d[off_o + i:off_o + i + 4])[0]
            b = struct.unpack("<I", dc.d[off_c + i:off_c + i + 4])[0]
            va = va0 + i
            mark = "  " if i in diffs else " ~"
            lines.append("  %s0x%08X  %08X %-40s -> %08X %-40s"
                         % (mark, va, a, dis(a, va), b, dis(b, va)))
    txt = "\n".join(lines)
    open(os.path.join(OUT, "diff_ranges.txt"), "w", encoding="utf-8").write(txt)
    print(txt[:1500])
    print("... (%d lines) -> dump/diff_ranges.txt" % len(lines))


def side(lo, hi, label=""):
    do = Elf(ORIG)
    dc = Elf(CUR)
    lines = ["=== side-by-side 0x%08X..0x%08X  %s ===" % (lo, hi, label),
             "  %-18s | %-38s | %-38s" % ("VA", "ORIG (EN retail)", "CUR (ZH113b)")]
    for va in range(lo, hi, 4):
        a = do.word(va)
        b = dc.word(va)
        mark = "**" if a != b else "  "
        lines.append("%s%08X %08X %-38s | %08X %-38s"
                     % (mark, va, a, dis(a, va), b, dis(b, va)))
    txt = "\n".join(lines)
    fn = "side_%08X_%08X.txt" % (lo, hi)
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(txt)
    print(txt)
    print("-> dump/%s" % fn)


def jmap():
    """for every `j <target>` in CUR that is not in ORIG, print the 8 bytes before it
    (original function head) plus the cave body."""
    do = Elf(ORIG)
    dc = Elf(CUR)
    va0, _, fs = dc.text()
    lines = []
    for va in range(va0, va0 + fs - 4, 4):
        w = dc.word(va)
        if (w >> 26) & 0x3F != 2:
            continue
        tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
        if do.word(va) == w:
            continue
        lines.append("\n=== j-patch 0x%08X -> 0x%08X   (ORIG was: %s)"
                     % (va, tgt, dis(do.word(va), va)))
        for v in range(va - 16, va + 8, 4):
            lines.append("    ctx %08X  orig=%08X %-36s cur=%08X %-36s"
                         % (v, do.word(v), dis(do.word(v), v), dc.word(v), dis(dc.word(v), v)))
        for v in range(tgt, tgt + 0x60, 4):
            lines.append("    cave %08X  %08X  %s" % (v, dc.word(v), dis(dc.word(v), v)))
    txt = "\n".join(lines)
    open(os.path.join(OUT, "jmap.txt"), "w", encoding="utf-8").write(txt)
    print("-> dump/jmap.txt  (%d patch points)" % txt.count("j-patch"))


def writes():
    dc = Elf(CUR)
    lines = []
    for (lo, hi, label) in CAVE_RANGES:
        lines.append("\n=== %s   0x%08X..0x%08X ===" % (label, lo, hi))
        for va in range(lo, hi, 4):
            w = dc.word(va)
            op = (w >> 26) & 0x3F
            if op in (0x28, 0x29, 0x2B, 0x3F, 0x39, 0x2A, 0x2E):   # sb sh sw sd swc1 swl swr
                lines.append("  %08X  %08X  %s" % (va, w, dis(w, va)))
    txt = "\n".join(lines)
    open(os.path.join(OUT, "writes.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    m = sys.argv[1]
    if m == "ranges":
        ranges()
    elif m == "side":
        side(int(sys.argv[2], 16), int(sys.argv[3], 16),
             sys.argv[4] if len(sys.argv) > 4 else "")
    elif m == "jmap":
        jmap()
    elif m == "writes":
        writes()
    else:
        raise SystemExit(__doc__)
