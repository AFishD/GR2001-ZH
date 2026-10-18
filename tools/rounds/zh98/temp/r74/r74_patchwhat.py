# r74_patchwhat.py - READ-ONLY. Decode what the localization byte patches DO.
# Reads elf_diff.txt (VA: oldbyte->newbyte) and reports, per patch site, the
# original and patched 32-bit instruction word at the containing aligned VA.
import os
import re
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "rounds", "zh98", "temp", "r74"))
import r74_mips as M  # noqa: E402

DIFF = REPO + r"\work\builds\GR_ZH118\temp\elf_diff.txt"
EN_ELF = REPO + r"\work\builds\GR_ZH98\temp\r74\SLUS_206.13.EN.elf"


def load_diff(path):
    """returns list of (va, oldbyte, newbyte)"""
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.strip()
            m = re.match(r"^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2})$", ln)
            if m:
                out.append((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)))
    return out


def main():
    zh = M.Elf(M.ELF)
    diffs = load_diff(DIFF)
    print("elf_diff.txt entries: %d" % len(diffs))

    # per-4KB-page histogram
    pages = {}
    for va, _, _ in diffs:
        pages[va >> 12] = pages.get(va >> 12, 0) + 1
    print("")
    print("=== patch density per 4KB page (top 24) ===")
    for p, c in sorted(pages.items(), key=lambda kv: -kv[1])[:24]:
        print("   0x%05Xxxx  %5d bytes" % (p, c))

    # which aligned words are touched
    words = {}
    for va, ob, nb in diffs:
        wva = va & ~3
        words.setdefault(wva, []).append((va, ob, nb))
    print("")
    print("=== aligned words touched: %d ===" % len(words))

    # Do any touched words look like CODE (i.e. inside a function)?  We can't know
    # for sure, but a changed byte in the LOW 3 bytes of a word that also has
    # other words nearby changed = likely data.  Report the 'isolated' ones
    # (single word, neighbours untouched) which are the best code-change candidates.
    allw = set(words.keys())
    isolated = [w for w in allw
                if (w - 4) not in allw and (w + 4) not in allw]
    print("   isolated (single-word) patch sites: %d" % len(isolated))
    print("")
    print("=== isolated sites, decoded as MIPS (Chinese ELF) ===")
    for w in sorted(isolated):
        old = zh.word(w)
        # rebuild the English word: apply inverse of the diff at this word only
        b = bytearray(struct.pack("<I", old))
        for va, ob, nb in words[w]:
            b[va - w] = ob
        en = struct.unpack("<I", bytes(b))[0]
        if en == old:
            continue
        print("  0x%08X  EN 0x%08X %-38s" % (w, en, M.dis(en, w)))
        print("             ZH 0x%08X %-38s" % (old, M.dis(old, w)))

    # Group contiguous runs to see if whole functions were replaced
    print("")
    print("=== contiguous patch runs (>4 bytes) ===")
    vals = sorted(allw)
    runs = []
    if vals:
        s = p = vals[0]
        for w in vals[1:]:
            if w == p + 4:
                p = w
            else:
                runs.append((s, p))
                s = p = w
        runs.append((s, p))
    big = [(a, b) for a, b in runs if b - a >= 16]
    print("   runs longer than 16 bytes: %d" % len(big))
    for a, b in big[:40]:
        n = sum(1 for w in allw if a <= w <= b)
        print("     0x%08X..0x%08X  span=%d  touched_words=%d" % (a, b, b - a + 4, n))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
