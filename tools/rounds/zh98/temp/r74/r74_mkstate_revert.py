# r74_mkstate_revert.py - READ-ONLY on inputs. Build a .p2s whose eeMemory.bin has
# all 1850 localization byte patches reverted to the English-original values, so
# RAM holds the ORIGINAL game code while the game state (heap included) is unchanged.
#
# Usage: python r74_mkstate_revert.py <src.p2s> <dst.p2s>
import os
import re
import sys
import zipfile

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as P  # noqa: E402

DIFF = os.path.join(REPO, "work", "builds", "GR_ZH118", "temp", "elf_diff.txt")
# ELF main segment: PT_LOAD off=0x80 vaddr=0x00100000  =>  RAM[va] = file[va - 0x100000 + 0x80]
# and the file VA space maps 1:1 onto EE RAM physical addresses.
RAM_LO, RAM_HI = 0x00100000, 0x00100000 + 0x4DED00


def main():
    src, dst = sys.argv[1], sys.argv[2]
    ram = bytearray(P.read_entry(src, "eeMemory.bin"))
    print("src eeMemory.bin = %d B" % len(ram))

    n = 0
    skipped = 0
    with open(DIFF, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = re.match(r"^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2})\s*$", ln.strip())
            if not m:
                continue
            va, old, new = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
            if not (RAM_LO <= va < RAM_HI):
                skipped += 1
                continue
            ram[va] = old
            n += 1
    print("reverted %d bytes in RAM (skipped %d outside ELF main segment)" % (n, skipped))

    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as out:
        for info in infos:
            data = bytes(ram) if info.filename == "eeMemory.bin" else P.read_entry(src, info.filename)
            if info.filename == "PCSX2 Savestate Version.id":
                out.writestr(zipfile.ZipInfo(info.filename), data, compress_type=zipfile.ZIP_STORED)
            else:
                out.writestr(info.filename, data, compress_type=zipfile.ZIP_DEFLATED)
    print("wrote %s (%d B)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
