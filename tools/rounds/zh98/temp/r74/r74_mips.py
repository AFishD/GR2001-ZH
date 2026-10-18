# r74_mips.py - R5900/MMI-aware MIPS disassembler + function finder + caller finder.
# READ-ONLY on the ELF.  Used to reconstruct the function containing the 492.88s crash PC.
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ELF = REPO + r"\work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf"

# ELF PT_LOAD[0]: off=0x80 vaddr=0x00100000 filesz=0x4DED00  ->  VA = off - 0x80 + 0x100000
VA_BASE = 0x00100000
OFF_BASE = 0x0080
TEXT_VA_END = 0x00100000 + 0x4DED00

GPR = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]

MMI0 = {0x00: "madd", 0x01: "maddu", 0x04: "plzcw", 0x10: "mfhi1", 0x11: "mthi1",
        0x12: "mflo1", 0x13: "mtlo1", 0x18: "mult1", 0x19: "multu1", 0x1A: "div1",
        0x1B: "divu1", 0x20: "madd1", 0x21: "maddu1", 0x28: "pcpyld", 0x29: "pcpyud",
        0x2A: "pceqb", 0x2B: "pceqh", 0x2C: "pceqw", 0x2D: "pcgtb", 0x2E: "pcgth",
        0x2F: "pcgtw", 0x30: "paddb", 0x31: "paddh", 0x32: "paddw", 0x34: "psubb",
        0x35: "psubh", 0x36: "psubw", 0x38: "pmaxh", 0x39: "pmaxw", 0x3A: "pcpyh",
        0x3B: "pcpyw"}
MMI1 = {0x01: "pabsh", 0x02: "pabsw", 0x03: "pceqw2", 0x10: "paddh2", 0x11: "paddw2",
        0x12: "paddb2", 0x14: "psubh2", 0x15: "psubw2", 0x16: "psubb2", 0x18: "pand",
        0x19: "por", 0x1A: "pxor", 0x1B: "pnor", 0x1C: "pmsubw", 0x1D: "phmadh",
        0x1E: "phmsbh", 0x20: "pexew", 0x21: "prevh", 0x22: "pextlw", 0x23: "ppacw",
        0x24: "pextuw", 0x26: "pcpyh2", 0x27: "prot3w"}
MMI2 = {0x30: "pmultw", 0x31: "pdivw", 0x34: "pmaddh", 0x35: "phmaddh",
        0x36: "phmsubh", 0x37: "pmadduw"}
MMI3 = {0x00: "pmfhi", 0x01: "pmflo", 0x02: "pinth", 0x03: "pmultuw",
        0x04: "pdivuw", 0x10: "pmthi", 0x11: "pmtlo", 0x12: "pexeh",
        0x13: "pcpyud2", 0x14: "pextuw2", 0x15: "pcpyld2", 0x16: "pextlh",
        0x17: "pextrh"}


def dis(insn, pc):
    op = (insn >> 26) & 0x3F
    rs = (insn >> 21) & 0x1F
    rt = (insn >> 16) & 0x1F
    rd = (insn >> 11) & 0x1F
    sa = (insn >> 6) & 0x1F
    fn = insn & 0x3F
    imm = insn & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    tgt = ((insn & 0x3FFFFFF) << 2) | (pc & 0xF0000000)
    r = GPR
    if op == 0x00:
        if fn == 0x00:
            return "nop" if insn == 0 else "sll $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x02: return "srl $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x03: return "sra $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x04: return "sllv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x06: return "srlv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x07: return "srav $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x08: return "jr $%s" % r[rs]
        if fn == 0x09: return "jalr $%s" % r[rs] + ("" if rd in (0, 31) else " -> $%s" % r[rd])
        if fn == 0x0A: return "movz $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x0B: return "movn $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x0C: return "syscall"
        if fn == 0x0D: return "break"
        if fn == 0x0F: return "sync"
        if fn == 0x10: return "mfhi $%s" % r[rd]
        if fn == 0x11: return "mthi $%s" % r[rs]
        if fn == 0x12: return "mflo $%s" % r[rd]
        if fn == 0x13: return "mtlo $%s" % r[rs]
        if fn == 0x14: return "dsllv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x16: return "dsrlv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x17: return "dsrav $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x18: return "mult $%s, $%s" % (r[rs], r[rt])
        if fn == 0x19: return "multu $%s, $%s" % (r[rs], r[rt])
        if fn == 0x1A: return "div $%s, $%s" % (r[rs], r[rt])
        if fn == 0x1B: return "divu $%s, $%s" % (r[rs], r[rt])
        if fn == 0x1C: return "madd $%s, $%s" % (r[rs], r[rt])
        if fn == 0x1D: return "maddu"
        if fn == 0x1E: return "plzcw"
        if fn == 0x20: return "add $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x21: return "addu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x22: return "sub $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x23: return "subu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x24: return "and $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x25: return "or $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x26: return "xor $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x27: return "nor $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2A: return "slt $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2B: return "sltu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2C: return "dadd"
        if fn == 0x2D: return "daddu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2E: return "dsub"
        if fn == 0x2F: return "dsubu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x38: return "dsll $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3A: return "dsrl $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3B: return "dsra $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3C: return "dsll32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3E: return "dsrl32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3F: return "dsra32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        return "special fn=0x%02x (0x%08x)" % (fn, insn)
    if op == 0x01:
        names = {0x00: "bltz", 0x01: "bgez", 0x02: "bltzl", 0x03: "bgezl",
                 0x08: "tgei", 0x10: "bltzal", 0x11: "bgezal", 0x12: "bltzall",
                 0x13: "bgezall"}
        nm = names.get(rt, "regimm rt=%d" % rt)
        return "%s $%s, %+d -> 0x%08X" % (nm, r[rs], simm * 4 + 4, pc + 4 + simm * 4)
    if op == 0x02: return "j 0x%08X" % tgt
    if op == 0x03: return "jal 0x%08X" % tgt
    if op == 0x04: return "beq $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm * 4 + 4, pc + 4 + simm * 4)
    if op == 0x05: return "bne $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm * 4 + 4, pc + 4 + simm * 4)
    if op == 0x06: return "blez $%s, %+d -> 0x%08X" % (r[rs], simm * 4 + 4, pc + 4 + simm * 4)
    if op == 0x07: return "bgtz $%s, %+d -> 0x%08X" % (r[rs], simm * 4 + 4, pc + 4 + simm * 4)
    if op == 0x08: return "addi $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x09: return "addiu $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0A: return "slti $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0B: return "sltiu $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0C: return "andi $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0D: return "ori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0E: return "xori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0F: return "lui $%s, 0x%04X" % (r[rt], imm)
    if op == 0x10:
        cf = {0: "mfc0", 4: "mtc0"}.get(rs, "cop0rs%d" % rs)
        return "%s $%s, $%s" % (cf, r[rt], r[rd])
    if op == 0x12:
        cf = {0: "mfc2", 2: "cfc2", 4: "mtc2", 6: "ctc2"}.get(rs, "cop2rs%d" % rs)
        return "%s $%s, $%s" % (cf, r[rt], r[rd])
    if op == 0x16: return "cop2 bc%s" % ("f" if rt == 0 else "t")
    if op == 0x18:
        return {0x00: "mfsa", 0x08: "mtsa"}.get(fn, "sa fn=0x%x" % fn)
    if op == 0x1C:
        grp = (insn >> 6) & 0x1F
        tbl = {0x00: "MMI", 0x01: "MMI1", 0x02: "MMI2", 0x03: "MMI3"}.get(insn & 7)
        if insn & 7 == 0:
            nm = MMI0.get(fn, "?")
            if nm in ("pcpyld", "pcpyud"):
                return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
            return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
        if insn & 7 == 1:
            return "%s $%s, $%s, $%s" % (MMI1.get(fn, "?"), r[rd], r[rs], r[rt])
        if insn & 7 == 2:
            return "%s $%s, $%s, $%s" % (MMI2.get(fn, "?"), r[rd], r[rs], r[rt])
        if insn & 7 == 3:
            nm = MMI3.get(fn, "?")
            if nm in ("pmfhi", "pmflo", "pinth"):
                return "%s $%s" % (nm, r[rd])
            return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
        return "SPECIAL2 0x%08x" % insn
    if op == 0x1F:
        if fn == 0x00: return "lq $%s, %d($%s)" % (r[rt], simm, r[rs])
        if fn == 0x1F: return "sq $%s, %d($%s)" % (r[rt], simm, r[rs])
        return "SPECIAL(op0x1F) fn=0x%02x" % fn
    if op == 0x20: return "lb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x21: return "lh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x23: return "lw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x24: return "lbu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x25: return "lhu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x26: return "lwl"
    if op == 0x27: return "lwu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2B: return "sw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x28: return "sb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x29: return "sh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2E: return "swr"
    if op == 0x2F: return "cache"
    if op == 0x31: return "lwc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x39: return "swc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x37: return "ld $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x3F: return "sd $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x33: return "lwc2"
    if op == 0x3B: return "swc2"
    if op == 0x36: return "lqc2 $vf%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x3E: return "sqc2 $vf%d, %d($%s)" % (rt, simm, r[rs])
    return "op=0x%02x 0x%08x" % (op, insn)


class Elf:
    def __init__(self, path):
        self.d = open(path, "rb").read()

    def read_va(self, va, n):
        off = va - VA_BASE + OFF_BASE
        return self.d[off:off + n]

    def word(self, va):
        return struct.unpack("<I", self.read_va(va, 4))[0]

    def va2off(self, va):
        return va - VA_BASE + OFF_BASE

    def find_word_all(self, value, lo_va=VA_BASE, hi_va=TEXT_VA_END):
        """find every 4-byte little-endian word equal to value, aligned to 4"""
        out = []
        lo = self.va2off(lo_va)
        hi = self.va2off(hi_va)
        start = lo + ((4 - (lo % 4)) % 4)
        blob = self.d
        needle = struct.pack("<I", value)
        i = start
        while i + 4 <= hi:
            j = blob.find(needle, i, hi)
            if j < 0:
                break
            if (j - OFF_BASE) % 4 == 0:
                out.append(j - OFF_BASE + VA_BASE)
            i = j + 1
        return out


def find_callers(elf, target):
    """scan all jal instructions in .text and report those targeting `target`."""
    out = []
    va = VA_BASE
    end = TEXT_VA_END - 4
    while va < end:
        w = elf.word(va)
        if (w >> 26) == 0x03:
            t = ((w & 0x3FFFFFF) << 2) | (va & 0xF0000000)
            if t == target:
                out.append(va)
        va += 4
    return out


def main():
    elf = Elf(ELF)
    mode = sys.argv[1]

    if mode == "findstart":
        # locate plausible function prologues = addiu sp,sp,-N  (op=0x09, rs=29, rt=29)
        lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
        for va in range(lo, hi, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            if op == 0x09 and rs == 29 and rt == 29:
                print("  prologue candidate 0x%08X  %s" % (va, dis(w, va)))

    elif mode == "dis":
        lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
        for va in range(lo, hi, 4):
            w = elf.word(va)
            print("  %08x  %08x  %s" % (va, w, dis(w, va)))

    elif mode == "callers":
        tgt = int(sys.argv[2], 16)
        cs = find_callers(elf, tgt)
        print("jal callers of 0x%08X : %d" % (tgt, len(cs)))
        for c in cs:
            print("   from 0x%08X" % c)

    elif mode == "wordhits":
        v = int(sys.argv[2], 16)
        hits = elf.find_word_all(v)
        print("word 0x%08X appears at %d VAs:" % (v, len(hits)))
        for h in hits[:60]:
            print("   0x%08X" % h)

    elif mode == "autofunc":
        # walk backwards from the crash PC to the nearest prologue candidate
        start = int(sys.argv[2], 16)
        va = start
        found = None
        while va > start - 0x800:
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            if op == 0x09 and rs == 29 and rt == 29:
                found = va
                break
            va -= 4
        print("nearest prologue below 0x%08X = %s" % (start, "0x%08X" % found if found else "none"))
        if found:
            for v in range(found, found + 0x100, 4):
                w = elf.word(v)
                print("  %08x  %s" % (v, dis(w, v)))
    else:
        raise SystemExit("modes: findstart|dis|callers|wordhits|autofunc")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
