"""r73_hardcoded_offsets.py -- does the ELF hardcode MENU.IMG internal offsets?

Why it matters: if the ELF contains absolute offsets *inside* MENU.IMG, then any entry
whose size changes shifts the following entries and the game breaks (a documented
observed hang). That would make "grow COMMON.PAK to fit a taller atlas" impossible
without also relocating the whole container index.

Read-only.
"""
import struct
import sys

ELF = r"work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf"

# candidate offsets worth hunting for (from the project's own reports + tcslib constants)
CAND = {
    0xB9120: "MENU.IMG offset of FONT.RES (入口 #4)",
    0x58431: "COMMON.PAK 内 new_font_revised 记录偏移",
    0x61D0F: "COMMON.PAK 记录链结束哨兵位置",
    0x4044C: "new_font_revised 记录长度",
    0x40010: "像素容器长度",
    0x61D13: "COMMON.PAK 总长",
    0x1031: "new_font_revised 记录起点",
}


def main():
    with open(ELF, "rb") as f:
        data = f.read()
    e_phoff = struct.unpack_from("<I", data, 0x1C)[0]
    e_phnum = struct.unpack_from("<H", data, 0x2C)[0]
    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * 0x20
        t, o, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", data, off)
        if t == 1 and fs:
            segs.append((va, o, fs))
    va0, off0, fs0 = segs[0]
    seg = data[off0:off0 + fs0]
    print(f"main segment VA 0x{va0:X} file off 0x{off0:X} size 0x{fs0:X}")

    for val, label in CAND.items():
        hits = []
        for pat in (struct.pack("<I", val), struct.pack(">I", val)):
            start = 0
            while True:
                i = seg.find(pat, start)
                if i < 0:
                    break
                hits.append(va0 + i)
                start = i + 1
        hits = sorted(set(hits))
        print(f"\n0x{val:X}  ({label}) -> {len(hits)} hit(s)")
        for h in hits[:20]:
            print(f"    VA 0x{h:08X}")

    # a broader sweep: any 32-bit word in the .data/.rodata tail that looks like a small
    # MENU.IMG-internal offset is too noisy; instead look for the FONT.RES entry *table*:
    # the container index is a run of {off,stored,real} triples. Search for 0xB9120 near
    # 0x58431-ish values inside the same 64-byte window.
    print("\n--- windows containing 0xB9120 (FONT.RES slot off) ---")
    for i in range(0, fs0 - 64, 4):
        if struct.unpack_from("<I", seg, i)[0] == 0xB9120:
            lo = max(0, i - 32)
            words = [struct.unpack_from("<I", seg, j)[0] for j in range(lo, i + 48, 4)]
            print(f"  VA 0x{va0+i:08X}: " + " ".join(f"{w:08X}" for w in words))


main()
