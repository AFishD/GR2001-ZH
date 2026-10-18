# -*- coding: utf-8 -*-
r"""cave_dis.py -- R5900/MMI-aware MIPS disassembler + ELF loader for the cave audit.

READ-ONLY on every ELF/ISO it touches.

Used by tools/re/toolbelt/cave_audit.py.  Written for round79 ("cave count vs bytes" audit).
Deliberately standalone (no Ghidra) so every quoted instruction in the report can be
re-produced byte-for-byte from the on-disk ELF.

CLI
---
  python cave_dis.py <elf> dis <loVA> <hiVA>        # linear disassembly
  python cave_dis.py <elf> diso <loVA> <hiVA>       # same, but print raw bytes too
  python cave_dis.py <elf> jtargets                 # every `j`/`jal` in .text -> target
  python cave_dis.py <elf> callers <targetVA>       # every `jal <target>` site
  python cave_dis.py <elf> word <VA>                # single word
  python cave_dis.py <elf> bytes <VA> <n>           # raw hex
  python cave_dis.py <elf> segs                     # program headers
"""
import struct
import sys

GPR = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]
FPR = ["f%d" % i for i in range(32)]

MMI0 = {0x00: "madd", 0x01: "maddu", 0x02: "madd", 0x03: "maddu", 0x04: "plzcw",
        0x10: "mfhi1", 0x11: "mthi1", 0x12: "mflo1", 0x13: "mtlo1",
        0x18: "mult1", 0x19: "multu1", 0x1A: "div1", 0x1B: "divu1",
        0x20: "madd1", 0x21: "maddu1", 0x28: "pcpyld", 0x29: "pcpyud",
        0x2A: "pceqb", 0x2B: "pceqh", 0x2C: "pceqw", 0x2D: "pcgtb", 0x2E: "pcgth",
        0x2F: "pcgtw", 0x30: "paddb", 0x31: "paddh", 0x32: "paddw", 0x34: "psubb",
        0x35: "psubh", 0x36: "psubw", 0x38: "pmaxh", 0x39: "pmaxw", 0x3A: "pcpyh",
        0x3B: "pcpyw"}
MMI1 = {0x01: "pabsh", 0x02: "pabsw", 0x03: "pceqw", 0x10: "paddh", 0x11: "paddw",
        0x12: "paddb", 0x14: "psubh", 0x15: "psubw", 0x16: "psubb", 0x18: "pand",
        0x19: "por", 0x1A: "pxor", 0x1B: "pnor", 0x1C: "pmsubw", 0x1D: "phmadh",
        0x1E: "phmsbh", 0x20: "pexew", 0x21: "prevh", 0x22: "pextlw", 0x23: "ppacw",
        0x24: "pextuw", 0x26: "pcpyh", 0x27: "prot3w"}
MMI2 = {0x30: "pmultw", 0x31: "pdivw", 0x34: "pmaddh", 0x35: "phmaddh",
        0x36: "phmsubh", 0x37: "pmadduw"}
MMI3 = {0x00: "pmfhi", 0x01: "pmflo", 0x02: "pinth", 0x03: "pmultuw",
        0x04: "pdivuw", 0x10: "pmthi", 0x11: "pmtlo", 0x12: "pexeh",
        0x13: "pcpyud", 0x14: "pextuw", 0x15: "pcpyld", 0x16: "pextlh",
        0x17: "pextrh", 0x18: "pinteh", 0x19: "pintoh"}

COP1_S = {0x00: "add.s", 0x01: "sub.s", 0x02: "mul.s", 0x03: "div.s", 0x04: "sqrt.s",
          0x05: "abs.s", 0x06: "mov.s", 0x07: "neg.s", 0x16: "rsqrt.s",
          0x18: "adda.s", 0x19: "suba.s", 0x1A: "mula.s", 0x1C: "madd.s", 0x1D: "msub.s",
          0x20: "cvt.s.w", 0x21: "cvt.s.d", 0x24: "cvt.w.s"}
COP1_W = {0x20: "cvt.s.w", 0x24: "cvt.w.s"}
COP1_CMP = {0x30: "c.f", 0x31: "c.un", 0x32: "c.eq", 0x33: "c.ueq", 0x34: "c.olt",
            0x35: "c.ult", 0x36: "c.ole", 0x37: "c.ule", 0x38: "c.sf", 0x39: "c.ngle",
            0x3A: "c.seq", 0x3B: "c.ngl", 0x3C: "c.lt", 0x3D: "c.nge", 0x3E: "c.le",
            0x3F: "c.ngt"}


def dis(w, pc):
    """Decode one R5900 instruction word at virtual address pc. Returns text."""
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    rd = (w >> 11) & 0x1F
    sa = (w >> 6) & 0x1F
    fn = w & 0x3F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    tgt = ((w & 0x03FFFFFF) << 2) | (pc & 0xF0000000)
    r = GPR
    if op == 0x00:
        if fn == 0x00:
            return "nop" if w == 0 else "sll $%s, $%s, %d" % (r[rd], r[rt], sa)
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
        if fn == 0x1D: return "maddu $%s, $%s" % (r[rs], r[rt])
        if fn == 0x1E: return "plzcw $%s, $%s" % (r[rd], r[rs])
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
        if fn == 0x2C: return "dadd $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2D: return "daddu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2E: return "dsub $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x2F: return "dsubu $%s, $%s, $%s" % (r[rd], r[rs], r[rt])
        if fn == 0x38: return "dsll $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3A: return "dsrl $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3B: return "dsra $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3C: return "dsll32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3E: return "dsrl32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x3F: return "dsra32 $%s, $%s, %d" % (r[rd], r[rt], sa)
        return "special fn=0x%02x (0x%08x)" % (fn, w)
    if op == 0x01:
        names = {0x00: "bltz", 0x01: "bgez", 0x02: "bltzl", 0x03: "bgezl",
                 0x08: "tgei", 0x09: "tgeiu", 0x0A: "tlti", 0x0B: "tltiu",
                 0x0C: "teqi", 0x0E: "tnei",
                 0x10: "bltzal", 0x11: "bgezal", 0x12: "bltzall", 0x13: "bgezall"}
        nm = names.get(rt, "regimm rt=%d" % rt)
        if rt in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0E):
            return "%s $%s, %d" % (nm, r[rs], simm)
        return "%s $%s, %+d -> 0x%08X" % (nm, r[rs], simm, pc + 4 + simm * 4)
    if op == 0x02: return "j 0x%08X" % tgt
    if op == 0x03: return "jal 0x%08X" % tgt
    if op == 0x04: return "beq $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm, pc + 4 + simm * 4)
    if op == 0x05: return "bne $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm, pc + 4 + simm * 4)
    if op == 0x06: return "blez $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + simm * 4)
    if op == 0x07: return "bgtz $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + simm * 4)
    if op == 0x08: return "addi $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x09: return "addiu $%s, $%s, %d (0x%04X)" % (r[rt], r[rs], simm, imm)
    if op == 0x0A: return "slti $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0B: return "sltiu $%s, $%s, %d (0x%04X)" % (r[rt], r[rs], simm, imm)
    if op == 0x0C: return "andi $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0D: return "ori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0E: return "xori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0F: return "lui $%s, 0x%04X" % (r[rt], imm)
    if op == 0x10:  # COP0
        cf = {0x00: "mfc0", 0x04: "mtc0"}.get(rs, "cop0rs%d" % rs)
        return "%s $%s, $%s" % (cf, r[rt], r[rd])
    if op == 0x11:  # COP1
        if rs == 0x00: return "mfc1 $%s, %s" % (r[rt], FPR[rd])
        if rs == 0x02: return "cfc1 $%s, $%s" % (r[rt], r[rd])
        if rs == 0x04: return "mtc1 $%s, %s" % (r[rt], FPR[rd])
        if rs == 0x06: return "ctc1 $%s, $%s" % (r[rt], r[rd])
        if rs == 0x08:
            return {0: "bc1f", 1: "bc1t", 2: "bc1fl", 3: "bc1tl"}.get(rt, "bc1?") + \
                " %+d -> 0x%08X" % (simm, pc + 4 + simm * 4)
        if rs == 0x10 or rs == 0x14:  # S / W
            fs = rd
            ft = rt
            if fn == 0x20: return "cvt.s.w %s, %s" % (FPR[rd if rs == 0x14 else rd], FPR[rd])
            if fn == 0x24: return "cvt.w.s %s, %s" % (FPR[rd], FPR[rd])
            if fn in COP1_CMP:
                return "%s %s, %s" % (COP1_CMP[fn], FPR[rd], FPR[rt])
            nm = COP1_S.get(fn, "cop1fn%02x" % fn)
            if fn in (0x05, 0x06, 0x07, 0x04):
                return "%s %s, %s" % (nm, FPR[rd], FPR[rd] if fn == 0x04 else FPR[rt])
            return "%s %s, %s, %s" % (nm, FPR[rd], FPR[rd], FPR[rt])
        return "cop1 rs=0x%02x fn=0x%02x (0x%08x)" % (rs, fn, w)
    if op == 0x12:
        cf = {0x00: "mfc2", 0x02: "cfc2", 0x04: "mtc2", 0x06: "ctc2"}.get(rs, "cop2rs%d" % rs)
        return "%s $%s, $%s" % (cf, r[rt], r[rd])
    if op == 0x16: return "cop2 bc%s" % ("f" if rt == 0 else "t")
    if op == 0x18:
        return {0x00: "mfsa $%s" % r[rd], 0x08: "mtsa $%s" % r[rs]}.get(fn, "sa fn=0x%x" % fn)
    if op == 0x1C:
        grp = w & 7
        if grp == 0:
            nm = MMI0.get(fn, "?")
            if nm in ("mfhi1", "mflo1", "plzcw"):
                return "%s $%s" % (nm, r[rd])
            return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
        if grp == 1:
            return "%s $%s, $%s, $%s" % (MMI1.get(fn, "?"), r[rd], r[rs], r[rt])
        if grp == 2:
            return "%s $%s, $%s, $%s" % (MMI2.get(fn, "?"), r[rd], r[rs], r[rt])
        if grp == 3:
            nm = MMI3.get(fn, "?")
            if nm in ("pmfhi", "pmflo", "pinth"):
                return "%s $%s" % (nm, r[rd])
            return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
        return "SPECIAL2 0x%08x" % w
    if op == 0x1F:
        if fn == 0x00: return "lq $%s, %d($%s)" % (r[rt], simm, r[rs])
        if fn == 0x1F: return "sq $%s, %d($%s)" % (r[rt], simm, r[rs])
        return "SPECIAL3 fn=0x%02x" % fn
    if op == 0x20: return "lb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x21: return "lh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x22: return "lwl $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x23: return "lw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x24: return "lbu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x25: return "lhu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x26: return "lwr $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x27: return "lwu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x28: return "sb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x29: return "sh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2A: return "swl $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2B: return "sw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2C: return "sdl $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2D: return "sdr $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2E: return "swr $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2F: return "cache 0x%x, %d($%s)" % (rt, simm, r[rs])
    if op == 0x31: return "lwc1 %s, %d($%s)" % (FPR[rt], simm, r[rs])
    if op == 0x39: return "swc1 %s, %d($%s)" % (FPR[rt], simm, r[rs])
    if op == 0x33: return "lwc2 $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x3B: return "swc2 $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x36: return "lqc2 vf%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x3E: return "sqc2 vf%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x37: return "ld $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x3F: return "sd $%s, %d($%s)" % (r[rt], simm, r[rs])
    return "op=0x%02x (0x%08x)" % (op, w)


class Elf:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.d = f.read()
        self.path = path
        e_phoff = struct.unpack_from("<I", self.d, 0x1C)[0]
        e_phentsize = struct.unpack_from("<H", self.d, 0x2A)[0]
        e_phnum = struct.unpack_from("<H", self.d, 0x2C)[0]
        self.segs = []
        for i in range(e_phnum):
            o = e_phoff + i * e_phentsize
            t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", self.d, o)
            if t == 1 and fs:
                self.segs.append((va, off, fs))
        self.entry = struct.unpack_from("<I", self.d, 0x18)[0]

    def va2off(self, va):
        for (v, o, fs) in self.segs:
            if v <= va < v + fs:
                return o + (va - v)
        raise KeyError("VA 0x%08X not in any PT_LOAD" % va)

    def read(self, va, n):
        o = self.va2off(va)
        return self.d[o:o + n]

    def word(self, va):
        return struct.unpack("<I", self.read(va, 4))[0]

    def text(self):
        """first PT_LOAD (the executable segment) as (va, off, size)"""
        return self.segs[0]

    def iter_words(self, lo, hi):
        for va in range(lo, hi, 4):
            yield va, self.word(va)


def find_jtargets(elf):
    """all j/jal targets inside the first PT_LOAD, as {target: [sites]}"""
    va0, off, fs = elf.text()
    out = {}
    for va in range(va0, va0 + fs - 4, 4):
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        if op in (2, 3):
            t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            out.setdefault(t, []).append(va)
    return out


def callers(elf, target):
    out = []
    va0, off, fs = elf.text()
    for va in range(va0, va0 + fs - 4, 4):
        w = elf.word(va)
        if ((w >> 26) & 0x3F) == 3:
            if (((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)) == target:
                out.append(va)
    return out


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    elf = Elf(sys.argv[1])
    mode = sys.argv[2]
    if mode == "segs":
        print("entry=0x%08X" % elf.entry)
        for (v, o, fs) in elf.segs:
            print("  PT_LOAD va=0x%08X off=0x%08X filesz=0x%08X" % (v, o, fs))
    elif mode == "dis":
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        for va, w in elf.iter_words(lo, hi):
            print("  %08x  %08x  %s" % (va, w, dis(w, va)))
    elif mode == "diso":
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        for va, w in elf.iter_words(lo, hi):
            print("  %08x  %08x  %-42s ; %s" % (va, w, dis(w, va),
                                                elf.read(va, 4).hex()))
    elif mode == "word":
        va = int(sys.argv[3], 16)
        print("0x%08X = 0x%08X  %s" % (va, elf.word(va), dis(elf.word(va), va)))
    elif mode == "bytes":
        va, n = int(sys.argv[3], 16), int(sys.argv[4], 16)
        print(elf.read(va, n).hex())
    elif mode == "callers":
        t = int(sys.argv[3], 16)
        cs = callers(elf, t)
        print("jal callers of 0x%08X : %d" % (t, len(cs)))
        for c in cs:
            print("   from 0x%08X" % c)
    elif mode == "jtargets":
        jt = find_jtargets(elf)
        patched = [t for t in jt if len(jt[t]) == 1]
        print("total j/jal targets: %d" % len(jt))
        for t in sorted(jt):
            print("  0x%08X  x%d  sites=%s" % (t, len(jt[t]),
                                               ",".join("0x%08X" % s for s in jt[t][:6])))
    else:
        raise SystemExit("modes: segs|dis|diso|word|bytes|callers|jtargets")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
