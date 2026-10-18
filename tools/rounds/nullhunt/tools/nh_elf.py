# -*- coding: utf-8 -*-
r"""nh_elf.py — 只读 ELF 解析 (SLUS_206.13) + VA<->文件偏移 + 符号表

用于把 emulog 里的 pc=0x1024d0 / 0x102584 归到具体函数。
"""
import os
import struct

EM_NAMES = {
    0: 'SHT_NULL', 1: 'PROGBITS', 2: 'SYMTAB', 3: 'STRTAB', 4: 'RELA',
    8: 'NOBITS', 9: 'REL',
}
STT = {0: 'NOTYPE', 1: 'OBJECT', 2: 'FUNC', 3: 'SECTION', 4: 'FILE'}


class Elf:
    def __init__(self, blob, tag=''):
        self.b = blob
        self.tag = tag
        assert blob[:4] == b'\x7fELF', 'not ELF'
        assert blob[4] == 1 and blob[5] == 1, 'expect ELF32 little endian'
        (self.type, self.machine, self.version, self.entry, self.phoff, self.shoff,
         self.flags, self.ehsize, self.phentsize, self.phnum, self.shentsize,
         self.shnum, self.shstrndx) = struct.unpack_from('<HHIIIIIHHHHHH', blob, 16)
        self.phdrs = []
        for i in range(self.phnum):
            p = self.phoff + i * self.phentsize
            (ptype, off, vaddr, paddr, filesz, memsz, flg, align) = \
                struct.unpack_from('<8I', blob, p)
            self.phdrs.append(dict(type=ptype, off=off, vaddr=vaddr, paddr=paddr,
                                   filesz=filesz, memsz=memsz, flags=flg, align=align))
        self.shdrs = []
        for i in range(self.shnum):
            p = self.shoff + i * self.shentsize
            (nm, typ, flg, addr, off, size, link, info, align, entsize) = \
                struct.unpack_from('<10I', blob, p)
            self.shdrs.append(dict(nameoff=nm, type=typ, flags=flg, addr=addr, off=off,
                                   size=size, link=link, info=info, align=align,
                                   entsize=entsize, idx=i))
        self.shstr = b''
        if self.shstrndx < len(self.shdrs):
            s = self.shdrs[self.shstrndx]
            self.shstr = blob[s['off']:s['off'] + s['size']]
        for s in self.shdrs:
            s['name'] = self._str(self.shstr, s['nameoff'])
        self.syms = []
        self._load_syms()

    @staticmethod
    def _str(tab, off):
        e = tab.find(b'\x00', off)
        return tab[off:e if e >= 0 else len(tab)].decode('latin-1')

    def _load_syms(self):
        for s in self.shdrs:
            if s['type'] != 2:                                  # SHT_SYMTAB
                continue
            strtab = self.shdrs[s['link']] if s['link'] < len(self.shdrs) else None
            st = self.b[strtab['off']:strtab['off'] + strtab['size']] if strtab else b''
            n = s['size'] // 16
            for i in range(n):
                p = s['off'] + i * 16
                nm, val, sz, info, other, shndx = struct.unpack_from('<IIIBBH', self.b, p)
                typ = info & 0xF
                self.syms.append(dict(name=self._str(st, nm), value=val, size=sz,
                                      type=typ, typname=STT.get(typ, str(typ)),
                                      bind=info >> 4, shndx=shndx, sec=s['name']))
        self.syms.sort(key=lambda x: (x['value'], -x['size']))

    # ------------------------------------------------------------------ 映射
    def va2off(self, va):
        for p in self.phdrs:
            if p['type'] != 1:
                continue
            if p['vaddr'] <= va < p['vaddr'] + p['filesz']:
                return p['off'] + (va - p['vaddr']), p
        return None, None

    def off2va(self, off):
        for p in self.phdrs:
            if p['type'] != 1:
                continue
            if p['off'] <= off < p['off'] + p['filesz']:
                return p['vaddr'] + (off - p['off']), p
        return None, None

    def sym_at(self, va):
        """→ 覆盖 va 的函数符号 (type FUNC 或 size>0), 选地址最大者"""
        best = None
        for s in self.syms:
            if s['value'] == 0 or s['value'] > va:
                continue
            if s['size'] and va < s['value'] + s['size']:
                if best is None or s['value'] > best['value']:
                    best = s
        if best:
            return best
        for s in self.syms:                                       # 退回最近的前一个
            if s['value'] and s['value'] <= va and (s['type'] == 2 or s['size']):
                if best is None or s['value'] > best['value']:
                    best = s
        return best

    def report_phdrs(self):
        out = []
        for i, p in enumerate(self.phdrs):
            out.append('  PH[%d] type=%d off=0x%X vaddr=0x%X filesz=0x%X memsz=0x%X flags=0x%X align=0x%X'
                       % (i, p['type'], p['off'], p['vaddr'], p['filesz'], p['memsz'],
                          p['flags'], p['align']))
            out.append('        VA 0x%X..0x%X  <->  FILE 0x%X..0x%X'
                       % (p['vaddr'], p['vaddr'] + p['filesz'], p['off'],
                          p['off'] + p['filesz']))
        return '\n'.join(out)

    def report_shdrs(self):
        out = []
        for s in self.shdrs:
            out.append('  SH[%2d] %-16s type=%-8s addr=0x%08X off=0x%08X size=0x%-8X entsize=0x%X'
                       % (s['idx'], s['name'], EM_NAMES.get(s['type'], str(s['type'])),
                          s['addr'], s['off'], s['size'], s['entsize']))
        return '\n'.join(out)


def mips_dis1(w, pc):
    """最小 MIPS32 反汇编 (仅覆盖本项目用到的常见指令)。返回字符串。"""
    op = w >> 26
    rs, rt, rd = (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
    sa, funct = (w >> 6) & 0x1F, w & 0x3F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    tgt = (w & 0x3FFFFFF) << 2
    R = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3',
         't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
         's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
         't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
    if w == 0:
        return 'nop'
    if op == 0:
        three = {0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu', 0x24: 'and',
                 0x25: 'or', 0x26: 'xor', 0x2A: 'slt', 0x2B: 'sltu', 0x18: 'mult',
                 0x19: 'multu', 0x1A: 'div', 0x1B: 'divu'}
        if funct in three:
            return '%s %s,%s,%s' % (three[funct], R[rd], R[rs], R[rt])
        if funct == 0x00:
            return 'sll %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x02:
            return 'srl %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x03:
            return 'sra %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x08:
            return 'jr %s' % R[rs]
        if funct == 0x09:
            return 'jalr %s,%s' % (R[rd], R[rs])
        if funct == 0x10:
            return 'mfhi %s' % R[rd]
        if funct == 0x12:
            return 'mflo %s' % R[rd]
        if funct == 0x0D:
            return 'break'
        if funct == 0x0C:
            return 'syscall'
        return 'op0 funct=0x%X' % funct
    simple = {2: 'j 0x%X' % tgt, 3: 'jal 0x%X' % tgt}
    if op in simple:
        return simple[op]
    if op == 4:
        return 'beq %s,%s,0x%X' % (R[rs], R[rt], pc + 4 + (simm << 2))
    if op == 5:
        return 'bne %s,%s,0x%X' % (R[rs], R[rt], pc + 4 + (simm << 2))
    if op == 6:
        return 'blez %s,0x%X' % (R[rs], pc + 4 + (simm << 2))
    if op == 7:
        return 'bgtz %s,0x%X' % (R[rs], pc + 4 + (simm << 2))
    if op in (1,):
        rtname = {0: 'bltz', 1: 'bgez', 16: 'bltzal', 17: 'bgezal'}.get(rt, 'regimm%d' % rt)
        return '%s %s,0x%X' % (rtname, R[rs], pc + 4 + (simm << 2))
    loads = {0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
             0x27: 'lwu', 0x1F: 'lq', 0x37: 'ld'}
    if op in loads:
        return '%s %s,%d(%s)' % (loads[op], R[rt], simm, R[rs])
    stores = {0x28: 'sb', 0x29: 'sh', 0x2B: 'sw', 0x3F: 'sq', 0x2F: 'sd'}
    if op in stores:
        return '%s %s,%d(%s)' % (stores[op], R[rt], simm, R[rs])
    alu = {0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu',
           0x0C: 'andi', 0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui'}
    if op in alu:
        if op == 0x0F:
            return 'lui %s,0x%X' % (R[rt], imm)
        return '%s %s,%s,%d' % (alu[op], R[rt], R[rs], simm)
    if op == 0x10:
        return 'cop0 %s' % ('mtc0' if rs == 4 else 'mfc0' if rs == 0 else '?')
    return 'op%d 0x%08X' % (op, w)


def dis(blob, va, count, off=None):
    """反汇编 count 条指令。blob=整个 ELF, va=起始 VA。"""
    out = []
    for i in range(count):
        a = va + i * 4
        if off is None:
            o, _ = Elf.va2off(None, a) if False else (None, None)
        # 直接线性映射: 由调用方给出 off 时才可靠; 这里用 p_offset 线性段
        out.append((a, 0))
    return out
