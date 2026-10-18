# -*- coding: utf-8 -*-
r"""dis2.py -- standalone R5900/MMI MIPS disassembler + ELF loader (READ-ONLY).

Written for GR_CULPRIT (round: culprit store).  Deliberately independent of
tools/re/toolbelt/cave_dis.py (which has a known "drops rd" bug); every operand of every
decoded instruction is emitted here.

CLI
---
  python dis2.py <elf> dis   <loVA> <hiVA>            linear disassembly
  python dis2.py <elf> diso  <loVA> <hiVA>            + raw bytes
  python dis2.py <elf> word  <VA> [...]               single words
  python dis2.py <elf> segs
  python dis2.py <elf> callers <targetVA>             jal/j sites to target
  python dis2.py <elf> funcstart <VA>                 scan back for a prologue
  python dis2.py <elf> immref <imm>                   lui/addiu pairs building an imm
  python dis2.py <elf> xref <VA>                      references to an absolute VA
"""
import struct
import sys

GPR = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]
FPR = ["f%d" % i for i in range(32)]

MMI0 = {0x00: "madd", 0x01: "maddu", 0x04: "plzcw",
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
          0x20: "cvt.s.w", 0x21: "cvt.s.d", 0x24: "cvt.w.s", 0x28: "max.s", 0x29: "min.s"}
COP1_W = {0x20: "cvt.s.w", 0x24: "cvt.w.s"}
COP1_CMP = {0x30: "c.f", 0x31: "c.un", 0x32: "c.eq", 0x33: "c.ueq", 0x34: "c.olt",
            0x35: "c.ult", 0x36: "c.ole", 0x37: "c.ule", 0x38: "c.sf", 0x39: "c.ngle",
            0x3A: "c.seq", 0x3B: "c.ngl", 0x3C: "c.lt", 0x3D: "c.nge", 0x3E: "c.le",
            0x3F: "c.ngt"}


def dis(w, pc):
    """Decode one R5900 word at virtual address pc. All operands emitted."""
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
        if fn == 0x09: return "jalr $%s%s" % (r[rs], "" if rd in (0, 31) else ", $%s" % r[rd])
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
    if op == 0x09: return "addiu $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0A: return "slti $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0B: return "sltiu $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0C: return "andi $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0D: return "ori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0E: return "xori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0F: return "lui $%s, 0x%04X" % (r[rt], imm)
    if op == 0x10:
        cf = {0x00: "mfc0", 0x04: "mtc0"}.get(rs, "cop0rs%d" % rs)
        return "%s $%s, $%s" % (cf, r[rt], r[rd])
    if op == 0x11:
        if rs == 0x00: return "mfc1 $%s, %s" % (r[rt], FPR[rd])
        if rs == 0x02: return "cfc1 $%s, $%s" % (r[rt], r[rd])
        if rs == 0x04: return "mtc1 $%s, %s" % (r[rt], FPR[rd])
        if rs == 0x06: return "ctc1 $%s, $%s" % (r[rt], r[rd])
        if rs == 0x08:
            return {0: "bc1f", 1: "bc1t", 2: "bc1fl", 3: "bc1tl"}.get(rt, "bc1?") + \
                " %+d -> 0x%08X" % (simm, pc + 4 + simm * 4)
        if rs in (0x10, 0x14):
            if fn == 0x20: return "cvt.s.w %s, %s" % (FPR[rd], FPR[rd])
            if fn == 0x24: return "cvt.w.s %s, %s" % (FPR[rd], FPR[rd])
            if fn in COP1_CMP: return "%s %s, %s" % (COP1_CMP[fn], FPR[rd], FPR[rt])
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
        if grp > 3:
            return "SPECIAL2 raw fn=0x%02x (0x%08x)" % (fn, w)
        tbl = (MMI0, MMI1, MMI2, MMI3)[grp]
        nm = tbl.get(fn, "mmi%d_%02x" % (grp, fn))
        if nm in ("mfhi1", "mflo1", "plzcw", "pmfhi", "pmflo", "pinth"):
            return "%s $%s" % (nm, r[rd])
        if nm in ("mthi1", "mtlo1", "pmthi", "pmtlo"):
            return "%s $%s" % (nm, r[rs])
        if nm in ("mult1", "multu1", "div1", "divu1", "madd1", "maddu1"):
            return "%s $%s, $%s" % (nm, r[rs], r[rt])
        return "%s $%s, $%s, $%s" % (nm, r[rd], r[rs], r[rt])
    # R5900: LQ = opcode 0x1F, SQ = opcode 0x1E, both plain I-type (offset in bits 15:0).
    if op == 0x1F: return "lq $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x1E: return "sq $%s, %d($%s)" % (r[rt], simm, r[rs])
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


def is_store(w):
    op = (w >> 26) & 0x3F
    if op in (0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x3F, 0x3B, 0x3E, 0x39, 0x1F):
        return True
    if op == 0x1F and (w & 0x3F) in (0x1F,):
        return True
    return False


def is_branch_or_jump(w):
    op = (w >> 26) & 0x3F
    if op in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07):
        return True
    if op == 0x00 and (w & 0x3F) in (0x08, 0x09):
        return True
    return False


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
                self.segs.append((va, off, fs, fl))
        self.entry = struct.unpack_from("<I", self.d, 0x18)[0]

    def va2off(self, va):
        for (v, o, fs, fl) in self.segs:
            if v <= va < v + fs:
                return o + (va - v)
        raise KeyError("VA 0x%08X not in any PT_LOAD" % va)

    def read(self, va, n):
        return self.d[self.va2off(va):self.va2off(va) + n]

    def word(self, va):
        return struct.unpack("<I", self.read(va, 4))[0]

    def has(self, va):
        for (v, o, fs, fl) in self.segs:
            if v <= va < v + fs:
                return True
        return False

    def text(self):
        return self.segs[0]

    def iter_words(self, lo, hi):
        for va in range(lo, hi, 4):
            yield va, self.word(va)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = Elf(sys.argv[1])
    mode = sys.argv[2]
    if mode == 'segs':
        print("entry=0x%08X" % elf.entry)
        for s in elf.segs:
            print("  PT_LOAD va=0x%08X off=0x%08X filesz=0x%08X flags=0x%X" % s)
    elif mode in ('dis', 'diso'):
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        for va, w in elf.iter_words(lo, hi):
            pre = "  %08x  %08x  " % (va, w)
            if mode == 'diso':
                print(pre + "%-52s ; %s" % (dis(w, va), elf.read(va, 4).hex()))
            else:
                print(pre + dis(w, va))
    elif mode == 'word':
        for s in sys.argv[3:]:
            va = int(s, 16)
            w = elf.word(va)
            print("  VA 0x%08X = 0x%08X  %s" % (va, w, dis(w, va)))
    elif mode == 'callers':
        want = set(int(x, 16) for x in sys.argv[3:])
        va0, _o, fsz, _fl = elf.text()
        for va in range(va0, va0 + fsz - 4, 4):
            w = elf.word(va)
            if ((w >> 26) & 0x3F) in (2, 3):
                t = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if t in want:
                    print('  0x%08X -> 0x%08X  %s' % (va, t, dis(w, va)))
    elif mode == 'funcstart':
        va = int(sys.argv[3], 16)
        for cand in range(va, va - 0x800, -4):
            w = elf.word(cand)
            # addiu $sp, $sp, -N   (op 9, rs=29, rt=29, simm<0)
            if ((w >> 26) & 0x3F) == 9 and ((w >> 21) & 0x1F) == 29 and ((w >> 16) & 0x1F) == 29:
                imm = w & 0xFFFF
                if imm & 0x8000:
                    print("  candidate prologue 0x%08X: %s" % (cand, dis(w, cand)))
    elif mode == 'immref':
        imm = int(sys.argv[3], 16)
        hi = (imm >> 16) & 0xFFFF
        lo = imm & 0xFFFF
        va0, _o, fsz, _fl = elf.text()
        for va in range(va0, va0 + fsz - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            if op == 0x0F and (w & 0xFFFF) == hi:
                rt = (w >> 16) & 0x1F
                nxt = elf.word(va + 4)
                if ((nxt >> 26) & 0x3F) in (0x09, 0x0D) and ((nxt >> 21) & 0x1F) == rt and (nxt & 0xFFFF) == lo:
                    print('  0x%08X  %s ; %s' % (va, dis(w, va), dis(nxt, va + 4)))
    elif mode == 'xref':
        va = int(sys.argv[3], 16)
        hi = (va >> 16) & 0xFFFF
        lo = va & 0xFFFF
        va0, _o, fsz, _fl = elf.text()
        for v in range(va0, va0 + fsz - 4, 4):
            w = elf.word(v)
            op = (w >> 26) & 0x3F
            if op == 0x0F and (w & 0xFFFF) == hi:
                rt = (w >> 16) & 0x1F
                nxt = elf.word(v + 4)
                if ((nxt >> 26) & 0x3F) in (0x09, 0x0D) and ((nxt >> 21) & 0x1F) == rt:
                    base = (hi << 16) + (nxt & 0xFFFF)
                    print('  0x%08X  builds 0x%08X (%s ; %s)' % (v, base, dis(w, v), dis(nxt, v + 4)))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
