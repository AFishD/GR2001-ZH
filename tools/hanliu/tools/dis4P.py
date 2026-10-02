# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/dis4P.py (逐字复制 (dis4 参数化变体))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""Complete PS2 EE (R5900) manual disassembler. Word-aligned, no capstone dependency."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import sys, struct, re, bisect
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_S.elf')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00
data = open(ELF,'rb').read()
main = data[SEC_OFF:SEC_OFF+SEC_SIZE]
strtab = data[0x4DEDE0:0x4DEDE0+0x13E199]
syms = {}
p, end = 0x61CF80, 0x61CF80+0x97420
while p < end:
    name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p); p += 16
    if name and value and SEC_ADDR <= value < SEC_ADDR+SEC_SIZE:
        n = strtab[name:strtab.index(b'\0',name)].decode('latin1')
        if value not in syms: syms[value] = n
fkeys = sorted(syms)
def fname(va):
    i = bisect.bisect_right(fkeys, va)-1
    if i>=0:
        k = fkeys[i]
        if 0 <= va-k < 0x8000: return "%s+0x%X" % (syms[k], va-k)
    return "sub_%08X" % va
strmap = {}
for m in re.finditer(rb'[\x20-\x7e]{4,}', main):
    strmap.setdefault(m.start()+SEC_ADDR, m.group().decode('latin1'))
R = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3','$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
     '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7','$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
FR = ['$f0','$f1','$f2','$f3','$f4','$f5','$f6','$f7','$f8','$f9','$f10','$f11','$f12','$f13','$f14','$f15',
      '$f16','$f17','$f18','$f19','$f20','$f21','$f22','$f23','$f24','$f25','$f26','$f27','$f28','$f29','$f30','$f31']
def si(x): return x-0x10000 if x>=0x8000 else x
def mem(rt, base, imm):
    return "%s, 0x%x(%s)" % (rt, imm & 0xffffffff if imm>=0 else imm, R[base])
MMI0 = {0:'paddw',1:'psubw',2:'pcgtw',3:'pmaxw',4:'paddh',5:'psubh',6:'pcgth',7:'pmaxh',8:'paddb',9:'psubb',
        10:'pcgtb',0x10:'paddsw',0x11:'psubsw',0x12:'pextlw',0x13:'ppacw',0x14:'paddsh',0x15:'psubsh',
        0x16:'pextlh',0x17:'ppach',0x18:'paddsb',0x19:'psubsb',0x1A:'pextlb',0x1B:'ppacb',
        0x1E:'pext5',0x1F:'ppac5'}
MMI1 = {1:'pabsw',2:'pceqw',3:'pminw',4:'padsbh',5:'pabsh',6:'pceqh',7:'pminh',10:'pceqb',
        0x14:'padduw',0x15:'psubuw',0x16:'pextuw',0x18:'paddub',0x19:'psubub',0x1A:'pextub',0x1B:'qfsrv'}
MMI2 = {0:'pmaddw',2:'psllvw',3:'psrlvw',4:'pmsubw',8:'pmfhi',9:'pmflo',0x0A:'pinth',0x0C:'pmultw',
        0x0D:'pdivw',0x0E:'pcpyld',0x10:'pmaddh',0x11:'phmadh',0x12:'pand',0x13:'pxor',0x14:'pmsubh',
        0x15:'phmsbh',0x1A:'pexeh',0x1B:'prevh',0x1C:'pmulth',0x1D:'pdivbw',0x1E:'pexew',0x1F:'prot3w'}
MMI3 = {0:'pmadduw',3:'psravw',8:'pmthi',9:'pmtlo',0x0A:'pinteh',0x0C:'pmultuw',0x0D:'pdivuw',
        0x0E:'pcpyud',0x12:'por',0x13:'pnor',0x1A:'pexch',0x1B:'pcpyh',0x1E:'pexcw'}
def ann_str(v):
    if v in strmap: return ' ; "%s"' % strmap[v][:70]
    if v in syms: return ' ; <%s>' % syms[v]
    return ''
def decode(w, va):
    op = w>>26; rs=(w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; sa=(w>>6)&31; fn=w&63
    imm = w&0xffff; simm=si(imm); tgt=(va+4+(simm<<2))&0xffffffff
    jtgt = ((va+4)&0xF0000000)|((w&0x3FFFFFF)<<2)
    if op==0x00:  # SPECIAL
        S={0:'sll',2:'srl',3:'sra',4:'sllv',6:'srlv',7:'srav',8:'jr',9:'jalr',10:'movz',11:'movn',
           12:'syscall',13:'break',15:'sync',16:'mfhi',17:'mthi',18:'mflo',19:'mtlo',
           24:'mult',25:'multu',26:'div',27:'divu',32:'add',33:'addu',34:'sub',35:'subu',
           36:'and',37:'or',38:'xor',39:'nor',40:'mfsa',41:'mtsa',42:'slt',43:'sltu',
           44:'dadd',45:'daddu',46:'dsub',47:'dsubu',52:'teq',56:'dsll',58:'dsrl',59:'dsra',
           60:'dsll32',62:'dsrl32',63:'dsra32'}
        n = S.get(fn)
        if fn==0 and w==0: return 'nop'
        if not n: return '.word 0x%08x' % w
        if fn in (0,2,3): return "%s %s, %s, 0x%x" % (n, R[rd], R[rt], sa)
        if fn in (4,6,7): return "%s %s, %s, %s" % (n, R[rd], R[rt], R[rs])
        if fn==8: return "jr %s" % R[rs]
        if fn==9: return "jalr %s, %s" % (R[rd], R[rs])
        if fn in (10,11): return "%s %s, %s, %s" % (n, R[rd], R[rs], R[rt])
        if fn in (16,18): return "%s %s" % (n, R[rd])
        if fn in (17,19): return "%s %s" % (n, R[rs])
        if fn in (24,25,26,27):  # EE: MULT/MULTU/DIV/DIVU with rd!=0 => 3-op mul (writes rd=LO)
            base = {24:'mult',25:'multu',26:'div',27:'divu'}[fn]
            if rd: return "%s(=mul) %s, %s, %s" % (base, R[rd], R[rs], R[rt])
            return "%s %s, %s" % (base, R[rs], R[rt])
        if fn in (32,33,34,35,36,37,38,39,42,43,44,45,46,47): return "%s %s, %s, %s" % (n, R[rd], R[rs], R[rt])
        if fn in (56,58,59): return "%s %s, %s, 0x%x" % (n, R[rd], R[rt], sa)
        if fn in (60,62,63): return "%s %s, %s, 0x%x" % (n, R[rd], R[rt], sa)
        if fn in (40,41): return "%s %s" % (n, R[rd] if fn==40 else R[rs])
        if fn==52: return "teq %s, %s" % (R[rs], R[rt])
        return "%s ?" % n
    if op==0x01:
        RI={0:'bltz',1:'bgez',2:'bltzl',3:'bgezl',16:'bltzal',17:'bgezal'}
        n=RI.get(rt)
        if not n: return '.word 0x%08x' % w
        return "%s %s, 0x%08x" % (n, R[rs], tgt)
    if op==0x02: return "j 0x%08x%s" % (jtgt, (' ; %s'%fname(jtgt) if jtgt in syms else ''))
    if op==0x03: return "jal 0x%08x%s" % (jtgt, (' ; %s'%fname(jtgt) if jtgt in syms else ''))
    if op==0x04: return "beq %s, %s, 0x%08x%s" % (R[rs], R[rt], tgt, ' ; %s'%fname(tgt) if (tgt in syms) else '')
    if op==0x05: return "bne %s, %s, 0x%08x" % (R[rs], R[rt], tgt)
    if op==0x06: return "blez %s, 0x%08x" % (R[rs], tgt)
    if op==0x07: return "bgtz %s, 0x%08x" % (R[rs], tgt)
    if op==0x08: return "addi %s, %s, 0x%x%s" % (R[rt], R[rs], simm, ann_str(simm))
    if op==0x09: return "addiu %s, %s, 0x%x%s" % (R[rt], R[rs], simm, ann_str(simm))
    if op==0x0A: return "slti %s, %s, 0x%x" % (R[rt], R[rs], simm)
    if op==0x0B: return "sltiu %s, %s, 0x%x" % (R[rt], R[rs], simm)
    if op==0x0C: return "andi %s, %s, 0x%x" % (R[rt], R[rs], imm)
    if op==0x0D: return "ori %s, %s, 0x%x%s" % (R[rt], R[rs], imm, ann_str(imm))
    if op==0x0E: return "xori %s, %s, 0x%x" % (R[rt], R[rs], imm)
    if op==0x0F: return "lui %s, 0x%x%s" % (R[rt], imm, ann_str(imm<<16))
    if op==0x10:
        if rs==0: return "mfc0 %s, $%d,%d" % (R[rt], rd, sa)
        if rs==4: return "mtc0 %s, $%d,%d" % (R[rt], rd, sa)
        return '.word 0x%08x (cop0)' % w
    if op==0x11:  # COP1
        if rs==0: return "mfc1 %s, %s" % (R[rt], FR[rd>>1 if False else rd])
        if rs==2: return "cfc1 %s, %s" % (R[rt], FR[rd])
        if rs==4: return "mtc1 %s, %s" % (R[rt], FR[rd])
        if rs==6: return "ctc1 %s, %s" % (R[rt], FR[rd])
        if rs==8:
            cc=(rt>>2)&7; bit=rt&1; nd=(rt>>1)&1
            n='bc1' + ('f' if bit==0 else 't') + ('l' if nd else '')
            return "%s 0x%08x" % (n, tgt)
        fmt=rs; F={16:'s',17:'d',20:'w'}
        f=F.get(fmt, str(fmt))
        fs_ = rt; ft_ = rd; fd_ = sa  # COP1 fmt ops: fs=bits20-16, ft=bits15-11, fd=bits10-6
        OP={0:'add',1:'sub',2:'mul',3:'div',4:'sqrt',5:'abs',6:'mov',7:'neg',
            0x20:'cvt.s' if fmt==20 else ('cvt.w' if fmt==16 else 'cvt.?'),
            50:'c.eq',60:'c.lt',62:'c.le'}
        n=OP.get(fn)
        if n is None: return '.word 0x%08x (cop1 fn=%x)' % (w, fn)
        if fn in (0,1,2,3):
            return "%s.%s %s, %s, %s" % (n, f, FR[fd_], FR[fs_], FR[ft_])
        if fn in (4,5,6,7):
            return "%s.%s %s, %s" % (n, f, FR[fd_], FR[fs_])
        if fn==0x20:
            return "cvt.s.w %s, %s" % (FR[fd_], FR[fs_]) if fmt==20 else "cvt.w.s %s, %s" % (FR[fd_], FR[fs_])
        return "%s.%s %s, %s" % (n, f, FR[fs_], FR[ft_])
    if op==0x12:
        if (w>>25)&1: return "v%02xop %08x" % (rs, w)
        if rs==8: return "mfc2? / qmfc2 %s, $vf%d" % (R[rt], rd)
        if rs==4: return "mtc2? / qmtc2 %s, $vf%d" % (R[rt], rd)
        return '.word 0x%08x (cop2)' % w
    if op in (0x14,0x15,0x16,0x17):
        n={0x14:'beql',0x15:'bnel',0x16:'blezl',0x17:'bgtzl'}[op]
        if op in (0x16,0x17): return "%s %s, 0x%08x" % (n, R[rs], tgt)
        return "%s %s, %s, 0x%08x" % (n, R[rs], R[rt], tgt)
    if op==0x18: return "daddi %s, %s, 0x%x" % (R[rt], R[rs], simm)
    if op==0x19: return "daddiu %s, %s, 0x%x" % (R[rt], R[rs], simm)
    if op==0x1A: return "ldl %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x1B: return "ldr %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x1C:  # MMI
        if fn==0x00: return "madd %s, %s" % (R[rs], R[rt])
        if fn==0x01: return "maddu %s, %s" % (R[rs], R[rt])
        if fn==0x04: return "plzcw %s, %s" % (R[rd], R[rs])
        if fn==0x08: return "mmi0.%s %s, %s, %s" % (MMI0.get(sa,'?'), R[rd], R[rs], R[rt])
        if fn==0x09: return "mmi2.%s %s, %s, %s" % (MMI2.get(sa,'?'), R[rd], R[rs], R[rt])
        if fn==0x10: return "mfhi1 %s" % R[rd]
        if fn==0x11: return "mthi1 %s" % R[rs]
        if fn==0x12: return "mflo1 %s" % R[rd]
        if fn==0x13: return "mtlo1 %s" % R[rs]
        if fn==0x18: return "mult1 %s, %s" % (R[rs], R[rt])
        if fn==0x19: return "multu1 %s, %s" % (R[rs], R[rt])
        if fn==0x1A: return "div1 %s, %s" % (R[rs], R[rt])
        if fn==0x1B: return "divu1 %s, %s" % (R[rs], R[rt])
        if fn==0x20: return "madd1 %s, %s" % (R[rs], R[rt])
        if fn==0x21: return "maddu1 %s, %s" % (R[rs], R[rt])
        if fn==0x28:
            if sa in MMI1: return "mmi1.%s %s, %s, %s%s" % (MMI1[sa], R[rd], R[rs], R[rt],
                                    '   ; (= %s copy)' % R[rs] if (rt==0 and MMI1[sa]=='paddub') else '')
            return 'mmi1.? sa=%d %08x' % (sa, w)
        if fn==0x29: return "mmi3.%s %s, %s, %s" % (MMI3.get(sa,'?'), R[rd], R[rs], R[rt])
        if fn==0x30: return "pmfhl ? %08x" % w
        if fn==0x31: return "pmthl ? %08x" % w
        if fn==0x34: return "psllh %s, %s, 0x%x" % (R[rd], R[rt], sa)
        if fn==0x36: return "psrlh %s, %s, 0x%x" % (R[rd], R[rt], sa)
        if fn==0x37: return "psrah %s, %s, 0x%x" % (R[rd], R[rt], sa)
        if fn==0x3C: return "psllw %s, %s, 0x%x" % (R[rd], R[rt], sa)
        if fn==0x3E: return "psrlw %s, %s, 0x%x" % (R[rd], R[rt], sa)
        if fn==0x3F: return "psraw %s, %s, 0x%x" % (R[rd], R[rt], sa)
        return 'mmi fn=%02x %08x' % (fn, w)
    if op==0x1E: return "lq %s, 0x%x(%s)" % (R[rt], simm&0xffffffff if simm>=0 else simm, R[rs])
    if op==0x1F: return "sq %s, 0x%x(%s)" % (R[rt], simm&0xffffffff if simm>=0 else simm, R[rs])
    if op==0x20: return "lb %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x21: return "lh %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x22: return "lwl %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x23: return "lw %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x24: return "lbu %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x25: return "lhu %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x26: return "lwr %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x27: return "lwu %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x28: return "sb %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x29: return "sh %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x2A: return "swl %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x2B: return "sw %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x2C: return "sdl %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x2D: return "sdr %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x2E: return "swr %s, 0x%x(%s)" % (R[rt], simm&0xffffffff, R[rs])
    if op==0x2F: return "cache ? %08x" % w
    if op==0x31: return "lwc1 %s, 0x%x(%s)" % (FR[rt], simm, R[rs])
    if op==0x35: return "ldc1 %s, 0x%x(%s)" % (FR[rt], simm, R[rs])
    if op==0x36: return "lqc2 $vf%d, 0x%x(%s)" % (rt, simm, R[rs])
    if op==0x37: return "ld %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    if op==0x39: return "swc1 %s, 0x%x(%s)" % (FR[rt], simm, R[rs])
    if op==0x3D: return "sdc1 %s, 0x%x(%s)" % (FR[rt], simm, R[rs])
    if op==0x3E: return "sqc2 $vf%d, 0x%x(%s)" % (rt, simm, R[rs])
    if op==0x3F: return "sd %s, 0x%x(%s)" % (R[rt], simm, R[rs])
    return '.word 0x%08x' % w
def dis(va, length):
    out=[]
    for a in range(0, length, 4):
        w = struct.unpack_from('<I', main, va-SEC_ADDR+a)[0]
        out.append("%08X  %s" % (va+a, decode(w, va+a)))
    return '\n'.join(out)
if __name__ == '__main__':
    va = int(sys.argv[1], 16)
    ln = int(sys.argv[2], 0) if len(sys.argv)>2 else 200
    print(dis(va, ln))
