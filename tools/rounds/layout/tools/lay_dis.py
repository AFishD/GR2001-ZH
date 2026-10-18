# -*- coding: utf-8 -*-
r"""lay_dis.py —— 【GR_LAYOUT】R5900 正确的反汇编器（只读）。

为什么需要它
------------
本工程既有的 `work\tools\cave_dis.py` 第 94 行把 SPECIAL `funct==0x18` 打印成
MIPS32 的**两操作数** `mult $rs, $rt`，**丢掉 rd 字段**。PS2 的 EE 核（R5900）
把 `funct 0x18/0x19/0x1A/0x1B` 定义成**三操作数**：

    MULT  rd, rs, rt      ; rd = (rs * rt)[31:0]
    MULTU rd, rs, rt
    DIV   rd, rs, rt      ; rd = rs / rt （商，截断）
    DIVU  rd, rs, rt

于是"`mult` 之后没有 `mflo`"这种读法是**反汇编器造成的假象**：乘积早已写进 rd。
本文件用正确的 R5900 语义重解码，并把同一字按 MIPS32 读法一并打印，便于逐条对照。

用法
----
  python lay_dis.py <elf> dis <loVA> <hiVA> [<loVA> <hiVA> ...]
  python lay_dis.py <elf> word <VA> [<VA> ...]
  python lay_dis.py <elf> callers <targetVA> [<targetVA> ...]
"""
import struct
import sys

GPR = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
       "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
       "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
       "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]

# SPECIAL 里被 R5900 改成三操作数的 funct
MULT3 = {0x18: 'mult', 0x19: 'multu', 0x1A: 'div', 0x1B: 'divu'}


class Elf(object):
    """最小 ELF32 读取器（用程序头推 VA→文件偏移，不硬编码）。"""

    def __init__(self, path):
        with open(path, 'rb') as f:
            self.d = f.read()
        if self.d[:4] != b'\x7fELF':
            raise SystemExit('不是 ELF: %s' % path)
        self.entry = struct.unpack_from('<I', self.d, 0x18)[0]
        e_phoff = struct.unpack_from('<I', self.d, 0x1C)[0]
        e_phentsize = struct.unpack_from('<H', self.d, 0x2A)[0]
        e_phnum = struct.unpack_from('<H', self.d, 0x2C)[0]
        self.segs = []
        for i in range(e_phnum):
            o = e_phoff + i * e_phentsize
            t, off, va, pa, fs, ms, fl, al = struct.unpack_from('<8I', self.d, o)
            if t == 1 and fs:
                self.segs.append((va, off, fs, fl))
        if not self.segs:
            raise SystemExit('没有 PT_LOAD')

    def va2off(self, va):
        for (v, o, s, _fl) in self.segs:
            if v <= va < v + s:
                return o + (va - v)
        raise SystemExit('VA 0x%08X 不在任何 PT_LOAD 内' % va)

    def word(self, va):
        return struct.unpack_from('<I', self.d, self.va2off(va))[0]

    def text(self):
        """返回 (va_lo, off, size) —— 取最大的可执行 PT_LOAD。"""
        best = None
        for (v, o, s, fl) in self.segs:
            if fl & 1:
                if best is None or s > best[2]:
                    best = (v, o, s)
        if best is None:
            best = max(self.segs, key=lambda x: x[2])
        return best


def dis_r5900(w, pc):
    """按 **R5900** 语义解码（三操作数 mult/div）。"""
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
        if fn in MULT3:
            return "%s $%s, $%s, $%s   ; ★R5900 三操作数: $%s = $%s %s $%s" % (
                MULT3[fn], r[rd], r[rs], r[rt], r[rd], r[rs],
                {'mult': '*', 'multu': '*u', 'div': '/', 'divu': '/u'}[MULT3[fn]], r[rt])
        if fn == 0x00:
            return "nop" if w == 0 else "sll $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x02: return "srl $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x03: return "sra $%s, $%s, %d" % (r[rd], r[rt], sa)
        if fn == 0x04: return "sllv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x06: return "srlv $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x07: return "srav $%s, $%s, $%s" % (r[rd], r[rt], r[rs])
        if fn == 0x08: return "jr $%s" % r[rs]
        if fn == 0x09: return "jalr $%s, $%s" % (r[rd] if rd else r[31], r[rs])
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
        return "special fn=0x%02X" % fn
    if op == 0x02: return "j 0x%08X" % tgt
    if op == 0x03: return "jal 0x%08X" % tgt
    if op == 0x04: return "beq $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm, pc + 4 + (simm << 2))
    if op == 0x05: return "bne $%s, $%s, %+d -> 0x%08X" % (r[rs], r[rt], simm, pc + 4 + (simm << 2))
    if op == 0x06: return "blez $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + (simm << 2))
    if op == 0x07: return "bgtz $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + (simm << 2))
    if op == 0x01:
        rtv = rt
        if rtv == 0: return "bltz $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + (simm << 2))
        if rtv == 1: return "bgez $%s, %+d -> 0x%08X" % (r[rs], simm, pc + 4 + (simm << 2))
        return "regimm rt=%d" % rtv
    if op == 0x08: return "addi $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x09: return "addiu $%s, $%s, %d (0x%04X)" % (r[rt], r[rs], simm, imm)
    if op == 0x0A: return "slti $%s, $%s, %d" % (r[rt], r[rs], simm)
    if op == 0x0B: return "sltiu $%s, $%s, %d (0x%04X)" % (r[rt], r[rs], simm, imm)
    if op == 0x0C: return "andi $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0D: return "ori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0E: return "xori $%s, $%s, 0x%04X" % (r[rt], r[rs], imm)
    if op == 0x0F: return "lui $%s, 0x%04X" % (r[rt], imm)
    if op == 0x10:
        if rs == 0x00: return "mfc0 $%s, $%d" % (r[rt], rd)
        return "cop0 rs=%d" % rs
    if op == 0x1C:
        return "MMI (op=0x1C) fn=0x%02X" % fn
    if op == 0x1F:
        return "cop1 ?"
    if op == 0x20: return "lb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x21: return "lh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x23: return "lw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x24: return "lbu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x25: return "lhu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x27: return "lwu $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x28: return "sb $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x29: return "sh $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2B: return "sw $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x2E: return "sq $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x37: return "ld $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x3F: return "sd $%s, %d($%s)" % (r[rt], simm, r[rs])
    if op == 0x31: return "lwc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x35: return "ldc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x39: return "swc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x3D: return "sdc1 $f%d, %d($%s)" % (rt, simm, r[rs])
    if op == 0x11:
        if rs == 0x04: return "mtc1 $%s, $f%d" % (r[rt], rd)
        if rs == 0x00: return "mfc1 $%s, $f%d" % (r[rt], rd)
        if rs == 0x08: return "bc1%s %+d -> 0x%08X" % (
            ['f', 't', 'fl', 'tl'][rt & 3], simm, pc + 4 + (simm << 2))
        if rs == 0x10:
            fn2 = w & 0x3F
            fd = (w >> 6) & 0x1F
            fs = (w >> 11) & 0x1F
            ft = (w >> 16) & 0x1F
            names = {0x00: 'add.s', 0x01: 'sub.s', 0x02: 'mul.s', 0x03: 'div.s',
                     0x04: 'sqrt.s', 0x05: 'abs.s', 0x06: 'mov.s', 0x07: 'neg.s',
                     0x16: 'rsqrt.s', 0x18: 'adda.s', 0x19: 'suba.s', 0x1A: 'mula.s',
                     0x1C: 'madd.s', 0x1D: 'msub.s', 0x20: 'cvt.s.w', 0x24: 'cvt.w.s'}
            if fn2 in names:
                if fn2 in (0x20, 0x24):
                    return "%s $f%d, $f%d" % (names[fn2], fd, fs)
                if fn2 in (0x04, 0x05, 0x06, 0x07, 0x16):
                    return "%s $f%d, $f%d" % (names[fn2], fd, fs)
                return "%s $f%d, $f%d, $f%d" % (names[fn2], fd, fs, ft)
            return "cop1.s fn=0x%02X" % fn2
    return "op=0x%02X" % op


def dis_mips32(w, pc):
    """同一字按 **MIPS32** 读法（= 既有 cave_dis.py 的口径），用于对照。"""
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    rd = (w >> 11) & 0x1F
    fn = w & 0x3F
    if op == 0x00 and fn == 0x18:
        return "mult $%s, $%s        ; (MIPS32 读法, rd 字段被丢弃)" % (GPR[rs], GPR[rt])
    if op == 0x00 and fn == 0x1A:
        return "div $%s, $%s         ; (MIPS32 读法, rd 字段被丢弃)" % (GPR[rs], GPR[rt])
    if op == 0x00 and fn == 0x19:
        return "multu $%s, $%s       ; (MIPS32 读法, rd 字段被丢弃)" % (GPR[rs], GPR[rt])
    if op == 0x00 and fn == 0x1B:
        return "divu $%s, $%s        ; (MIPS32 读法, rd 字段被丢弃)" % (GPR[rs], GPR[rt])
    return ''


def main():
    argv = sys.argv[:]
    out = None
    if '-o' in argv:
        i = argv.index('-o')
        out = argv[i + 1]
        del argv[i:i + 2]
    if out:
        sys.stdout = open(out, 'w', encoding='utf-8', newline='\n')
    else:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = Elf(argv[1])
    args = argv[2:]
    if not args:
        raise SystemExit(__doc__)
    mode = args[0]
    if mode == 'word':
        for s in args[1:]:
            va = int(s, 16)
            w = elf.word(va)
            print('  VA 0x%08X = 0x%08X  %s' % (va, w, dis_r5900(w, va)))
        return
    if mode == 'callers':
        va0, _o, fsz = elf.text()
        want = set(int(x, 16) for x in args[1:])
        for va in range(va0, va0 + fsz - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            if op in (2, 3):
                tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
                if tgt in want:
                    print('  0x%08X → 0x%08X  %s' % (va, tgt, dis_r5900(w, va)))
        return
    if mode == 'dis':
        rest = args[1:]
        for i in range(0, len(rest) - 1, 2):
            lo, hi = int(rest[i], 16), int(rest[i + 1], 16)
            print('=' * 100)
            print('# [0x%08X, 0x%08X)' % (lo, hi))
            for va in range(lo, hi, 4):
                w = elf.word(va)
                txt = dis_r5900(w, va)
                alt = dis_mips32(w, va)
                print('  %08x  %08x  %-62s %s' % (va, w, txt, alt))
        return
    raise SystemExit('未知模式 %r' % mode)


if __name__ == '__main__':
    main()
