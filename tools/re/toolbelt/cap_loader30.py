# -*- coding: utf-8 -*-
r"""cap_loader30.py -- round73 字库扩容裁决：把「+0x30 加载器记账」从【磁盘字节】上读透。

只读。输入 = 现役 ISO（ELF @LBA295 / 段偏移 0x80 / VA 基址 0x00100000）。
不依赖 Ghidra：自带 MIPS III/EE 子集解码器 + ELF 节/符号解析。

回答三个问题：
  Q1  UITexture+0x30 是谁写的？（LoadingTexturePak 0x51B660 / LoadPS2Img 0x51D910）
  Q2  UITexture+0x30 被谁读？（全 ELF `lw/sw $rt,0x30($rs)` 扫描 + 符号归属）
  Q3  这条记账在 h=512（现役）与 h=1024（L1 提案）下各自算出什么？会不会越界？

用法:
  python tools/re/toolbelt/cap_loader30.py [--iso PATH] [--json OUT]
"""
import argparse
import json
import os
import struct
import sys
import collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
ELF_LBA, SEC = 295, 2048

# ---------------------------------------------------------------- ELF 解析


class Elf:
    def __init__(self, data):
        self.d = data
        assert data[:4] == b'\x7fELF', 'not an ELF'
        (self.e_shoff,) = struct.unpack_from('<I', data, 0x20)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from('<HH', data, 0x2A)
        (self.e_shentsize, self.e_shnum, self.e_shstrndx) = struct.unpack_from('<HHH', data, 0x2E)
        # program headers
        self.phdrs = []
        for i in range(self.e_phnum):
            o = self.e_phoff + i * self.e_phentsize if hasattr(self, 'e_phoff') else None
            o = struct.unpack_from('<I', data, 0x1C)[0] + i * self.e_phentsize
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
                struct.unpack_from('<8I', data, o)
            self.phdrs.append(dict(type=p_type, off=p_offset, va=p_vaddr,
                                   filesz=p_filesz, memsz=p_memsz))
        # sections
        self.shdrs = []
        for i in range(self.e_shnum):
            o = self.e_shoff + i * self.e_shentsize
            f = struct.unpack_from('<10I', data, o)
            self.shdrs.append(dict(name=f[0], type=f[1], flags=f[2], addr=f[3],
                                   off=f[4], size=f[5], link=f[6], info=f[7]))
        shstr = self.shdrs[self.e_shstrndx]
        self.shnames = self._strtab(shstr['off'], shstr['size'])
        for s in self.shdrs:
            s['sname'] = self._cstr(self.shnames, s['name'])
        # symtab
        self.syms = []
        for s in self.shdrs:
            if s['type'] == 2:  # SYMTAB
                strtab = self.shdrs[s['link']]
                names = data[strtab['off']:strtab['off'] + strtab['size']]
                n = s['size'] // 16
                for i in range(n):
                    o = s['off'] + i * 16
                    nm, val, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, o)
                    if val:
                        self.syms.append(dict(name=self._cstr(names, nm), val=val,
                                              size=size, info=info, shndx=shndx))
                break
        self.syms.sort(key=lambda x: x['val'])

    @staticmethod
    def _cstr(buf, off):
        e = buf.find(b'\x00', off)
        return buf[off:e].decode('latin-1')

    def _strtab(self, off, size):
        return self.d[off:off + size]

    def va2off(self, va):
        for p in self.phdrs:
            if p['type'] == 1 and p['va'] <= va < p['va'] + p['filesz']:
                return p['off'] + (va - p['va'])
        raise KeyError('VA %08X not in any PT_LOAD' % va)

    def load_at(self, va, n):
        o = self.va2off(va)
        return self.d[o:o + n]

    def sym_at(self, va):
        lo, hi = 0, len(self.syms)
        best = None
        for s in self.syms:
            if s['val'] <= va:
                best = s
            else:
                break
        return best


# ------------------------------------------------------- MIPS III/EE 解码器

RT = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3',
      't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
      's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
      't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
RT = ['$' + r for r in RT]

IMM3 = {0x08: 'addiu', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu',
        0x0C: 'andi', 0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui',
        0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
        0x27: 'lwu', 0x28: 'sb', 0x29: 'sh', 0x2B: 'sw',
        0x1F: 'sq', 0x37: 'ld', 0x3F: 'sd', 0x27 | 0x100: 'lwu'}
REG3 = {0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu',
        0x24: 'and', 0x25: 'or', 0x26: 'xor', 0x27: 'nor',
        0x2A: 'slt', 0x2B: 'sltu', 0x2C: 'dadd', 0x2D: 'daddu',
        0x2E: 'dsub', 0x2F: 'dsubu',
        0x18: 'mult', 0x19: 'multu', 0x1A: 'div', 0x1B: 'divu',
        0x10: 'mfhi', 0x12: 'mflo'}
SHIFT = {0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x38: 'dsll', 0x3A: 'dsrl', 0x3C: 'dsll32', 0x3E: 'dsrl32'}
BR2 = {0x04: 'beq', 0x05: 'bne', 0x06: 'blez', 0x07: 'bgtz',
       0x14: 'beql', 0x15: 'bnel', 0x16: 'blezl', 0x17: 'bgtzl'}
COP1 = {0x00: 'mfc1', 0x02: 'cfc1', 0x04: 'mtc1', 0x06: 'ctc1'}


def sext(x, b=16):
    m = 1 << (b - 1)
    return (x ^ m) - m


def decode(w, pc):
    """Return (mnemonic_string, kind, info-dict)."""
    op = w >> 26
    rs, rt, rd = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
    sa, fn = (w >> 6) & 31, w & 63
    imm = w & 0xFFFF
    si = sext(imm)
    if w == 0:
        return 'nop', 'nop', {}
    if op == 0:
        if fn in SHIFT:
            return '%s %s,%s,%d' % (SHIFT[fn], RT[rd], RT[rt], sa), 'alu', {}
        if fn in REG3:
            if fn in (0x18, 0x19, 0x1A, 0x1B):
                return '%s %s,%s' % (REG3[fn], RT[rs], RT[rt]), 'mul', {}
            if fn in (0x10, 0x12):
                return '%s %s' % (REG3[fn], RT[rd]), 'mflo' if fn == 0x12 else 'mfhi', {}
            return '%s %s,%s,%s' % (REG3[fn], RT[rd], RT[rs], RT[rt]), 'alu', {}
        if fn == 0x08:
            return 'jr %s' % RT[rs], 'jr', {}
        if fn in (0x0A, 0x0B):
            return 'movz/movn %s,%s,%s' % (RT[rd], RT[rs], RT[rt]), 'alu', {}
        if fn == 0x09:
            return 'jalr %s' % RT[rd], 'call', {}
        if fn == 0x0D:
            return 'break', 'other', {}
        if fn == 0x0F:
            return 'sync', 'other', {}
        if fn == 0x28:
            return 'mmi.paddub %s,%s,%s' % (RT[rd], RT[rs], RT[rt]), 'alu', {}
        if fn == 0x25:
            return 'or(mmi?) %s,%s,%s' % (RT[rd], RT[rs], RT[rt]), 'alu', {}
        return 'special fn=0x%02X' % fn, 'other', {}
    if op in IMM3:
        mn = IMM3[op]
        if mn in ('lui',):
            return '%s %s,0x%X' % (mn, RT[rt], imm), 'lui', {'imm': imm}
        if mn[0] in 'ls':
            return '%s %s,0x%X(%s)' % (mn, RT[rt], imm, RT[rs]), 'mem', {'imm': imm, 'base': rs, 'rt': rt}
        if mn == 'andi':
            return '%s %s,%s,0x%X' % (mn, RT[rt], RT[rs], imm), 'alu', {}
        if mn in ('addiu',):
            return '%s %s,%s,%d' % (mn, RT[rt], RT[rs], si), 'addiu', {'imm': si, 'rs': rs, 'rt': rt}
        return '%s %s,%s,%d' % (mn, RT[rt], RT[rs], si), 'alu', {'imm': si}
    if op in BR2:
        tgt = pc + 4 + (si << 2)
        return '%s %s,%s,0x%08X' % (BR2[op], RT[rs], RT[rt] if op in (0x04, 0x05, 0x14, 0x15) else 'zero', tgt), 'br', {'tgt': tgt}
    if op in (0x02, 0x03):
        tgt = ((pc + 4) & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
        return '%s 0x%08X' % ('j' if op == 0x02 else 'jal', tgt), 'j', {'tgt': tgt}
    if op == 0x11:  # COP1
        if rs in COP1:
            return '%s %s,%s' % (COP1[rs], RT[rt], rd if rs in (0x00, 0x02) else RT[rd]), 'cop1', {}
        if rs == 0x08:
            return 'bc1 (imm 0x%X)' % imm, 'br', {}
        return 'cop1 rs=%d' % rs, 'other', {}
    if op == 0x1C:  # MMI
        return 'mmi op=0x1C fn=0x%02X' % fn, 'other', {}
    if op == 0x31:
        return 'lq %s,0x%X(%s)' % (RT[rt], imm, RT[rs]), 'mem', {'imm': imm, 'base': rs, 'rt': rt}
    if op == 0x3F:
        return 'sq %s,0x%X(%s)' % (RT[rt], imm, RT[rs]), 'mem', {'imm': imm, 'base': rs, 'rt': rt}
    return 'op=0x%02X word=%08X' % (op, w), 'other', {}


def dis(elf, va, count, annotate=None):
    out = []
    for i in range(count):
        pc = va + i * 4
        try:
            w = struct.unpack_from('<I', elf.load_at(pc, 4))[0]
        except KeyError:
            break
        s, kind, info = decode(w, pc)
        note = annotate(pc, s, kind, info) if annotate else ''
        out.append(dict(va=pc, word=w, text=s, kind=kind, note=note))
    return out


def fmt(rows):
    lines = []
    for r in rows:
        lines.append('%08X  %08X  %-34s %s' % (r['va'], r['word'], r['text'], r['note']))
    return lines


# ---------------------------------------------------------------- analytics

B_PRIME_DOC = ("B' = (0x10000/W) << 2  (磁盘字节实证: 0x51B978 / 0x5181D8 `sll $v0,$v0,2` "
               "作用于 divu 的商, 0x51B974 的 mult 是死码) ; DMA 单元 = B'+16")


def accounting(w, px_size):
    """Reproduce the loader formula + the SetTexturePkt chunker exactly (disk-byte semantics)."""
    if w == 0 or (0x10000 % w) and False:
        pass
    bprime = (0x10000 // w) << 2                    # 0x51B978 / 0x5181D8
    unit = bprime + 0x10                            # 0x51B97C
    c = -(-px_size // unit)                         # 0x51B988..0x51B994  ceil(P/(B'+16))
    f30 = px_size - c * 16                          # 0x51B998..0x51B9A4
    npackets = -(-f30 // bprime) if bprime else 0   # 0x5181E4..0x5181F8
    rem, delivered, addr, rows = f30, 0, 0, []
    for i in range(npackets):
        t1 = bprime if bprime < rem else rem        # 0x51821C-0x518230
        qwc = (t1 >> 4) + 1
        rows.append(dict(i=i, t1=t1, qwc=qwc, bytes=qwc * 16, addr=addr))
        delivered += qwc * 16
        addr += bprime + 16
        rem -= t1
    slack = c * unit - px_size
    return dict(w=w, px_size=px_size, px_size_hex='0x%X' % px_size, B_prime=bprime,
                unit=unit, c_units=c, f30=f30, f30_hex='0x%X' % f30,
                pixel_bytes=w * (px_size and 0) or None,
                npackets=npackets, delivered=delivered, delivered_hex='0x%X' % delivered,
                px_size_minus_delivered=px_size - delivered,
                slack_r=slack,
                short_16=(bprime < slack < unit),
                chunks=rows[:4] + ([{'...': '...'}] if len(rows) > 8 else []) + rows[-2:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=DEFAULT_ISO)
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r75', 'loader30.json'))
    args = ap.parse_args()

    with open(args.iso, 'rb') as f:
        f.seek(ELF_LBA * SEC)
        head = f.read(0x40)
        assert head[:4] == b'\x7fELF', 'ELF_LBA 处不是 ELF'
        (phoff,) = struct.unpack_from('<I', head, 0x1C)
        (phes, phn) = struct.unpack_from('<HH', head, 0x2A)
        (shoff,) = struct.unpack_from('<I', head, 0x20)
        (shes, shn) = struct.unpack_from('<HH', head, 0x2E)
        f.seek(ELF_LBA * SEC + phoff)
        ph = f.read(phes * phn)
        end = 0
        for i in range(phn):
            t, o, v, pa, fs_, ms, fl, al = struct.unpack_from('<8I', ph, i * phes)
            if t == 1:
                end = max(end, o + fs_)
        end = max(end, shoff + shn * shes)
        f.seek(ELF_LBA * SEC)
        elf_bytes = f.read(end)
    elf = Elf(elf_bytes)

    rep = dict(iso=args.iso, elf_size=len(elf_bytes),
               phdrs=[dict(off=p['off'], va=p['va'], filesz=p['filesz']) for p in elf.phdrs[:4]],
               b_prime_rule=B_PRIME_DOC)

    def symname(va):
        s = elf.sym_at(va)
        return (s['name'] or '?') + ('+0x%X' % (va - s['val']) if s and va != s['val'] else '') if s else '?'

    # ---- Q1/Q2: every `lw/sw/ld/sd $rt,0x30($rs)` in the UITexture/UIPacket module
    WINDOWS = [(0x517000, 0x520000, 'UITexture/UIPacket 模块'),
               (0x21A000, 0x220000, 'RSFont/RSFontMgr 模块'),
               (0x53A000, 0x53B000, 'DrawCharacter'),
               (0x416000, 0x418000, '汉化 cave 群')]
    hits = []
    for p in elf.phdrs:
        if p['type'] != 1:
            continue
        for off in range(0, p['filesz'], 4):
            va = p['va'] + off
            if not any(lo <= va < hi for lo, hi, _ in WINDOWS):
                continue
            w = struct.unpack_from('<I', elf_bytes, p['off'] + off)[0]
            s, kind, info = decode(w, va)
            if kind == 'mem' and info.get('imm') == 0x30:
                hits.append(dict(va=va, text=s, base=RT[info['base']],
                                 rw='W' if s.split()[0] in ('sw', 'sd', 'sq', 'sh', 'sb') else 'R',
                                 fn=symname(va)))
    rep['disp30_mem_ops_total'] = len(hits)
    byfn = collections.OrderedDict()
    for h in hits:
        byfn.setdefault(h['fn'] + ' [' + h['rw'] + ']', []).append('%08X %s' % (h['va'], h['text']))
    rep['disp30_by_function'] = byfn
    rep['disp30_writers'] = [h for h in hits if h['rw'] == 'W']
    rep['disp30_readers'] = [h for h in hits if h['rw'] == 'R']

    # ---- the three named sites, decoded from disk bytes
    SITES = {
        'cctc_grid_cave@0x417050': 0x417050,
        'LoadingTexturePak_acc@0x51B900': 0x51B900,
        'LoadPS2Img_acc@0x51DA60': 0x51DA60,
        'SetTexturePkt_chunk@0x5181B8': 0x5181B8,
        'SetTexturePkt_tex0@0x518828': 0x518828,
        'RefreshActive_30@0x51BF00': 0x51BF00,
        'LoadRSBFile_30@0x51CF60': 0x51CF60,
    }
    N = {'cctc_grid_cave@0x417050': 60, 'LoadingTexturePak_acc@0x51B900': 40,
         'LoadPS2Img_acc@0x51DA60': 32, 'SetTexturePkt_chunk@0x5181B8': 68,
         'SetTexturePkt_tex0@0x518828': 24, 'RefreshActive_30@0x51BF00': 40,
         'LoadRSBFile_30@0x51CF60': 20}
    rep['sites'] = {}
    for k, va in SITES.items():
        rows = dis(elf, va, N[k])
        rep['sites'][k] = dict(va=va, sym=symname(va),
                               text=fmt(rows),
                               asm=[dict(va=r['va'], word='%08X' % r['word'], text=r['text'])
                                    for r in rows])

    # ---- where does SetTexturePkt get `fp` (=0x10000?) and `a0` stride? find lui $fp
    fpdefs = []
    for off in range(0, 0x1E00, 4):
        va = 0x5176E0 + off
        w = struct.unpack_from('<I', elf.load_at(va, 4))[0]
        s, kind, info = decode(w, va)
        if kind == 'lui' and s.split()[1] == '$fp':
            fpdefs.append(dict(va=va, text=s))
        if kind == 'alu' and s.startswith('or(mmi?)') and '$fp' in s:
            fpdefs.append(dict(va=va, text=s))
    rep['settexturepkt_fp_defs'] = fpdefs

    # ---- Q3: the accounting, current vs L1
    rep['accounting'] = {
        'orig_EN_512x512_psmt8_px0x40010': accounting(512, 0x40010),
        'zh22H_512x512_psmt4_px0x20010': accounting(512, 0x20010),
        'SHIPPING_1024x512_psmt4_px0x40010': accounting(1024, 0x40010),
        'r73_R1_proposal_1024x1024_px0x80310': accounting(1024, 0x80310),
        'L1_two_unit_single_tag_px0x80010': accounting(1024, 0x80010),
        'L1_two_unit_16seg_px0x80020': accounting(1024, 0x80020),
    }

    txt = json.dumps(rep, indent=1, ensure_ascii=False, default=str)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)


main()
