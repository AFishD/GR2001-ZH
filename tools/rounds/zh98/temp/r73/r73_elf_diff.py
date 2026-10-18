"""r73_elf_diff.py -- whole-file diff of the ORIGINAL PS2 ELF vs the current (ZH-patched) ELF.

Read-only, prints to stdout. This is the authoritative map of *what the localization
patched inside the executable*, which is exactly the set of "levers" this task asks about.

Also disassembles the changed words with a small MIPS/EE decoder so the report can quote
real instructions instead of raw hex.
"""
import struct
import sys

ORIG = r"third_party\orig\ps2\slus_out\SLUS_206.13"
CUR = r"work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf"

REG = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]


def load(path):
    with open(path, "rb") as f:
        data = f.read()
    e_phoff = struct.unpack_from("<I", data, 0x1C)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x2A)[0]
    e_phnum = struct.unpack_from("<H", data, 0x2C)[0]
    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        t, o, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", data, off)
        if t == 1 and fs:
            segs.append((va, o, fs))
    return data, segs


def off_of(segs, va):
    for (v, o, fs) in segs:
        if v <= va < v + fs:
            return o + (va - v)
    return None


def dis(w, pc):
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    rd = (w >> 11) & 0x1F
    sa = (w >> 6) & 0x1F
    fn = w & 0x3F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    tgt = (pc & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
    if op == 0:
        S = {0x00: f"sll {REG[rd]},{REG[rt]},{sa}", 0x02: f"srl {REG[rd]},{REG[rt]},{sa}",
             0x03: f"sra {REG[rd]},{REG[rt]},{sa}", 0x08: f"jr {REG[rs]}",
             0x09: f"jalr {REG[rd]},{REG[rs]}", 0x10: f"mfhi {REG[rd]}",
             0x12: f"mflo {REG[rd]}", 0x18: f"mult {REG[rs]},{REG[rt]}",
             0x19: f"multu {REG[rs]},{REG[rt]}", 0x1A: f"div {REG[rs]},{REG[rt]}",
             0x1B: f"divu {REG[rs]},{REG[rt]}", 0x20: f"add {REG[rd]},{REG[rs]},{REG[rt]}",
             0x21: f"addu {REG[rd]},{REG[rs]},{REG[rt]}", 0x23: f"subu {REG[rd]},{REG[rs]},{REG[rt]}",
             0x24: f"and {REG[rd]},{REG[rs]},{REG[rt]}", 0x25: f"or {REG[rd]},{REG[rs]},{REG[rt]}",
             0x26: f"xor {REG[rd]},{REG[rs]},{REG[rt]}", 0x27: f"nor {REG[rd]},{REG[rs]},{REG[rt]}",
             0x2A: f"slt {REG[rd]},{REG[rs]},{REG[rt]}", 0x2B: f"sltu {REG[rd]},{REG[rs]},{REG[rt]}",
             0x3C: f"dsll32 {REG[rd]},{REG[rt]},{sa}", 0x3F: f"dsra32 {REG[rd]},{REG[rt]},{sa}"}
        return S.get(fn, f"special fn=0x{fn:02X}")
    if op == 1:
        return {0x00: f"bltz {REG[rs]},{pc+4+(simm<<2):#x}", 0x01: f"bgez {REG[rs]},{pc+4+(simm<<2):#x}",
                0x10: f"bltzal {REG[rs]},{pc+4+(simm<<2):#x}", 0x11: f"bgezal {REG[rs]},{pc+4+(simm<<2):#x}"} \
            .get(rt, f"regimm rt=0x{rt:02X}")
    if op == 2:
        return f"j {tgt:#010x}"
    if op == 3:
        return f"jal {tgt:#010x}"
    if op == 4:
        return f"beq {REG[rs]},{REG[rt]},{pc+4+(simm<<2):#x}"
    if op == 5:
        return f"bne {REG[rs]},{REG[rt]},{pc+4+(simm<<2):#x}"
    if op == 6:
        return f"blez {REG[rs]},{pc+4+(simm<<2):#x}"
    if op == 7:
        return f"bgtz {REG[rs]},{pc+4+(simm<<2):#x}"
    if op == 8:
        return f"addi {REG[rt]},{REG[rs]},{simm}"
    if op == 9:
        return f"addiu {REG[rt]},{REG[rs]},{simm}   (0x{imm:04X})"
    if op == 0xA:
        return f"slti {REG[rt]},{REG[rs]},{simm}"
    if op == 0xB:
        return f"sltiu {REG[rt]},{REG[rs]},{imm}  (0x{imm:04X})"
    if op == 0xC:
        return f"andi {REG[rt]},{REG[rs]},0x{imm:04X}"
    if op == 0xD:
        return f"ori {REG[rt]},{REG[rs]},0x{imm:04X}"
    if op == 0xE:
        return f"xori {REG[rt]},{REG[rs]},0x{imm:04X}"
    if op == 0xF:
        return f"lui {REG[rt]},0x{imm:04X}"
    if op == 0x10:
        return {0: f"mfc0 {REG[rt]},${rd}", 4: f"mtc0 {REG[rt]},${rd}"}.get(rs, f"cop0 rs={rs}")
    if op == 0x11:
        if rs == 4:
            return f"mtc1 {REG[rt]},f{rd}"
        if rs == 0:
            return f"mfc1 {REG[rt]},f{rd}"
        if rs == 0x10:
            return f"cvt.s.w f{rd},f{(w>>11)&0x1F}"
        if rs == 0x12:
            return f"add.s f{rd},f{(w>>11)&0x1F},f{rt}"
        if rs == 0x08:
            return "bc1"
        return f"cop1 rs={rs}"
    if op == 0x14:
        return f"beql {REG[rs]},{REG[rt]},{pc+4+(simm<<2):#x}"
    if op == 0x15:
        return f"bnel {REG[rs]},{REG[rt]},{pc+4+(simm<<2):#x}"
    if op == 0x1C:
        return f"mmi_special2 fn=0x{fn:02X} sa={sa}"
    if op == 0x1F:
        return f"mmi_special3 (w={w:08X})"
    if op == 0x20:
        return f"lb {REG[rt]},{simm}({REG[rs]})"
    if op == 0x21:
        return f"lh {REG[rt]},{simm}({REG[rs]})"
    if op == 0x23:
        return f"lw {REG[rt]},{simm}({REG[rs]})"
    if op == 0x24:
        return f"lbu {REG[rt]},{simm}({REG[rs]})"
    if op == 0x25:
        return f"lhu {REG[rt]},{simm}({REG[rs]})"
    if op == 0x27:
        return f"lwu {REG[rt]},{simm}({REG[rs]})"
    if op == 0x28:
        return f"sb {REG[rt]},{simm}({REG[rs]})"
    if op == 0x29:
        return f"sh {REG[rt]},{simm}({REG[rs]})"
    if op == 0x2B:
        return f"sw {REG[rt]},{simm}({REG[rs]})"
    if op == 0x31:
        return f"lwc1 f{rt},{simm}({REG[rs]})"
    if op == 0x39:
        return f"swc1 f{rt},{simm}({REG[rs]})"
    if op == 0x37:
        return f"ld {REG[rt]},{simm}({REG[rs]})"
    if op == 0x3F:
        return f"sd {REG[rt]},{simm}({REG[rs]})"
    return f"op=0x{op:02X}"


def main():
    do, so = load(ORIG)
    dc, sc = load(CUR)
    seg_o = so[0]
    seg_c = sc[0]
    print(f"orig seg vaddr={seg_o[0]:#x} off={seg_o[1]:#x} size={seg_o[2]:#x}")
    print(f"cur  seg vaddr={seg_c[0]:#x} off={seg_c[1]:#x} size={seg_c[2]:#x}")
    va0 = seg_c[0]
    n = min(seg_o[2], seg_c[2])
    diffs = []
    for i in range(0, n, 4):
        a = do[seg_o[1] + i: seg_o[1] + i + 4]
        b = dc[seg_c[1] + i: seg_c[1] + i + 4]
        if a != b:
            diffs.append((i, a, b))
    print(f"\n=== {len(diffs)} differing 4-byte words over {n} bytes "
          f"({100.0*len(diffs)*4/n:.4f}%) ===")

    # coalesce into ranges (gap <= 16 bytes)
    ranges = []
    for (i, a, b) in diffs:
        if ranges and i - ranges[-1][1] <= 16:
            ranges[-1][1] = i + 4
        else:
            ranges.append([i, i + 4])
    print(f"=== {len(ranges)} changed ranges (coalesced, gap<=16B) ===")
    for (s, e) in ranges:
        print(f"\n--- file off 0x{s:06X}..0x{e:06X}  VA 0x{va0+s:08X}..0x{va0+e:08X} "
              f"({e-s} B)")
        for i in range(s, e, 4):
            a = struct.unpack("<I", do[seg_o[1] + i: seg_o[1] + i + 4])[0]
            b = struct.unpack("<I", dc[seg_c[1] + i: seg_c[1] + i + 4])[0]
            va = va0 + i
            mark = "  " if i in [d[0] for d in diffs] else " ~"
            print(f"  {mark}0x{va:08X}  {a:08X} {dis(a, va):38s} -> "
                  f"{b:08X} {dis(b, va):38s}")


main()
