# r74_state_probe.py - READ-ONLY. Find EE register-PC and check whether the corrupt
# allocator pointers appear, in one or more p2s files.  Pure byte scan, no schema
# assumptions: we look for a plausible PC (inside the game's code window) and for
# the arena pointer family seen in the user's emulog.
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402

GAME_PC_LO, GAME_PC_HI = 0x00100000, 0x005E0000
SEARCH = [0x022D161C, 0x022D1624, 0x022D162C, 0x4154536F, 0x4154536B]


def main():
    for p2s in sys.argv[1:]:
        print("=" * 78)
        print("### %s  (mtime %s)" % (
            p2s, __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p2s))))
        regs = R.read_entry(p2s, "eeHwRegs.bin")
        print("  eeHwRegs.bin = %d B" % len(regs))
        # PC is the first u32 of the R5900 register block in PCSX2's EE hw regs
        cands = []
        for off in range(0, min(len(regs), 0x400) - 4, 4):
            v = struct.unpack_from("<I", regs, off)[0]
            if GAME_PC_LO <= v < GAME_PC_HI:
                cands.append((off, v))
        print("  plausible game PCs (u32 in 0x00100000..0x005E0000) inside first 0x400:")
        for off, v in cands[:14]:
            print("     +0x%03X = 0x%08X" % (off, v))
        ee = R.read_entry(p2s, "eeMemory.bin")
        print("  eeMemory.bin = %d B" % len(ee))
        for v in SEARCH:
            n = struct.pack("<I", v)
            c = ee.count(n)
            print("     u32 0x%08X -> %d hits" % (v, c))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
