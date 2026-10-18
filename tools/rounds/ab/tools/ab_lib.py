# -*- coding: utf-8 -*-
r"""ab_lib.py — GR_AB (最小 A/B 打靶盘) 共享库。**全部只读**既有盘。

复用 GR_NULLHUNT 的 nh_lib / nh_elf (只读 mmap) 与 tools/gr_tools 的 LZO 编解码。
只读对象: work/builds/GR_ZH113b/GR_ZH113b.iso, work/builds/GR_EN_ORIG/GR_EN_ORIG.iso,
          third_party/orig/ps2/*.iso
写入范围: work/builds/GR_AB/**  (本文件永不写既有盘)
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
NH_TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_NULLHUNT', 'tools')
for p in (NH_TOOLS, os.path.join(REPO, 'tools', 'gr_tools'),
          os.path.join(REPO, 'tools', 'text_csv'), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import nh_lib as N          # noqa: E402
import nh_elf as E          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_AB')
EVID = os.path.join(OUT, 'evidence')
SEC = N.SEC

BASE_ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
BASE_EN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
TRUE_ORIG = os.path.join(REPO, 'third_party', 'orig', 'ps2',
                         "Tom Clancy's Ghost Recon (USA).iso")

ISO = {'ZH113b': BASE_ZH, 'ZH113b_fix': N.ISO['ZH113b_fix'],
       'EN_ORIG': BASE_EN, 'TRUE_ORIG': TRUE_ORIG}

# ELF(SLUS_206.13) 在 ISO 里的起始字节: LBA 295
ELF_LBA = 295
ELF_ISO_BASE = ELF_LBA * SEC              # 0x93800, 自证见 docs/REPORT_NULLDEREF_ZH113b.md §1.1
VA2FILE = 0xFFF80                         # FILE = VA - 0xFFF80
# ⇒ ISO 偏移 = VA - 0x6C780  (与 docs/LEAD_CAPACITY_2400.md §1.1 一致)
VA2ISO = VA2FILE - ELF_ISO_BASE           # 0x6C780

IMG = {
    'MENU': '/MENU.IMG;1',
    'GR': '/GR.IMG;1',
}


def load_elf(tag):
    iso = N.Iso(ISO[tag])
    f = [v for k, v in iso.files().items() if 'SLUS_206.13' in k][0]
    blob = iso.rd(f['lba'] * SEC, f['size'])
    iso.close()
    return E.Elf(blob, tag), f


def va2file(va):
    return va - VA2FILE


def va2iso(va):
    return va - VA2ISO


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def md5(b):
    return hashlib.md5(b).hexdigest()


# ---------------------------------------------------------------- FONT.RES
def fontres_entry(iso, img_path):
    """→ (entry_dict, iso_base, raw_slot)  raw_slot = 盘上 entry['stored'] 字节"""
    f = iso.files()[img_path]
    lba = f['lba']
    base = lba * SEC
    ents, hdr, names = iso.img_entries(lba, None)
    e = [x for x in ents if x['name'] == 'FONT.RES'][0]
    raw = iso.rd(base + e['off'], e['stored'])
    return e, base, raw, ents


def decompress_fontres(raw):
    """raw = {u32 comp}{u32 real}{LZO 流}{尾部}  → (plain, comp, real, stream_end)"""
    import lz77_decode
    comp, real = struct.unpack_from('<II', raw, 0)
    stream = raw[8:8 + comp]
    dd, err, _ = lz77_decode.lzo1x_decompress(stream, real)
    return dd, comp, real, 8 + comp


# ---------------------------------------------------------------- MIPS 反汇编
R = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3',
     't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
     's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
     't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

# R5900 实测(本盘自证): 0x1E = LQ(读 16B)  0x1F = SQ(写 16B)  0x37 = LD  0x3F = SD
# 自证: DrawString 序言 0x219A78 = 7FBE0090(op0x1F=SQ fp,144) ; 尾声 0x219DC4 = 7BBE0090(op0x1E=LQ fp,144)
LOADS = {0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x27: 'lwu',
         0x1E: 'lq', 0x37: 'ld', 0x22: 'lwl', 0x26: 'lwr'}
STORES = {0x28: 'sb', 0x29: 'sh', 0x2B: 'sw', 0x1F: 'sq', 0x3F: 'sd', 0x2E: 'swr',
          0x2A: 'swl', 0x2D: 'sdr', 0x2C: 'sdl'}
ALUI = {0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu',
        0x0C: 'andi', 0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui'}
FPU_LWC = {0x31: 'lwc1', 0x35: 'ldc1', 0x39: 'swc1', 0x3D: 'sdc1'}


def dis1(w, pc):
    """MIPS32(r5900) 反汇编, 覆盖本项目 68 处差异用到的全部编码。"""
    op = w >> 26
    rs, rt, rd = (w >> 21) & 0x1F, (w >> 16) & 0x1F, (w >> 11) & 0x1F
    sa, funct = (w >> 6) & 0x1F, w & 0x3F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    tgt = (w & 0x3FFFFFF) << 2
    if w == 0:
        return 'nop'
    if op == 0:
        three = {0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu', 0x24: 'and',
                 0x25: 'or', 0x26: 'xor', 0x27: 'nor', 0x2A: 'slt', 0x2B: 'sltu',
                 0x18: 'mult', 0x19: 'multu', 0x1A: 'div', 0x1B: 'divu',
                 0x2C: 'dadd', 0x2D: 'daddu', 0x2E: 'dsub', 0x2F: 'dsubu'}
        if funct in three:
            return '%s %s,%s,%s' % (three[funct], R[rd], R[rs], R[rt])
        if funct == 0x00:
            return 'nop' if (rd == 0 and rt == 0 and sa == 0) else 'sll %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x02:
            return 'srl %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x03:
            return 'sra %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x04:
            return 'sllv %s,%s,%s' % (R[rd], R[rt], R[rs])
        if funct == 0x06:
            return 'srlv %s,%s,%s' % (R[rd], R[rt], R[rs])
        if funct == 0x07:
            return 'srav %s,%s,%s' % (R[rd], R[rt], R[rs])
        if funct == 0x08:
            return 'jr %s' % R[rs]
        if funct == 0x09:
            return 'jalr %s%s' % (R[rd], (',%s' % R[rs]) if rd != 31 else '')
        if funct == 0x10:
            return 'mfhi %s' % R[rd]
        if funct == 0x11:
            return 'mthi %s' % R[rs]
        if funct == 0x12:
            return 'mflo %s' % R[rd]
        if funct == 0x13:
            return 'mtlo %s' % R[rs]
        if funct == 0x0D:
            return 'break'
        if funct == 0x0C:
            return 'syscall'
        if funct == 0x3C:
            return 'dsll32 %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x3F:
            return 'dsra32 %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x3E:
            return 'dsrl32 %s,%s,%d' % (R[rd], R[rt], sa)
        if funct == 0x2C:
            return 'dadd %s,%s,%s' % (R[rd], R[rs], R[rt])
        if funct == 0x2D:
            return 'daddu %s,%s,%s' % (R[rd], R[rs], R[rt])
        return 'op0.funct0x%X' % funct
    if op == 2:
        return 'j 0x%X' % tgt
    if op == 3:
        return 'jal 0x%X' % tgt
    if op == 4:
        return 'beq %s,%s,0x%X' % (R[rs], R[rt], pc + 4 + (simm << 2))
    if op == 5:
        return 'bne %s,%s,0x%X' % (R[rs], R[rt], pc + 4 + (simm << 2))
    if op == 6:
        return 'blez %s,0x%X' % (R[rs], pc + 4 + (simm << 2))
    if op == 7:
        return 'bgtz %s,0x%X' % (R[rs], pc + 4 + (simm << 2))
    if op == 1:
        nm = {0: 'bltz', 1: 'bgez', 16: 'bltzal', 17: 'bgezal'}.get(rt, 'regimm%d' % rt)
        return '%s %s,0x%X' % (nm, R[rs], pc + 4 + (simm << 2))
    if op in LOADS:
        return '%s %s,%d(%s)' % (LOADS[op], R[rt], simm, R[rs])
    if op in STORES:
        return '%s %s,%d(%s)' % (STORES[op], R[rt], simm, R[rs])
    if op in ALUI:
        if op == 0x0F:
            return 'lui %s,0x%X' % (R[rt], imm)
        return '%s %s,%s,%d' % (ALUI[op], R[rt], R[rs], simm)
    if op == 0x10:
        nm = {0: 'mfc0', 4: 'mtc0'}.get(rs, 'cop0.rs%d' % rs)
        return '%s %s,%s' % (nm, R[rt], R[rd])
    if op == 0x11:
        return 'cop1.rs%d f%d,%s' % (rs, rd, R[rt])
    if op in FPU_LWC:
        return '%s f%d,%d(%s)' % (FPU_LWC[op], rt, simm, rs)
    # op 0x1C/0x1D: MMI (sq/lq 已被 op 0x1F/0x3F 覆盖); op 0x1E/0x1F special2
    if op == 0x1F:                    # SPECIAL3 (sq/lq/shuf) - 已由 STORES/LOADS 处理
        pass
    if op in (0x1C, 0x1D):
        mmi = {0x00: 'madd', 0x01: 'maddu', 0x02: 'mul', 0x04: 'div1', 0x10: 'mfhi1',
               0x11: 'mthi1', 0x12: 'mflo1', 0x13: 'mtlo1', 0x20: 'madd1', 0x21: 'maddu1'}
        return '%s %s,%s,%s' % (mmi.get(funct, 'mmi.funct0x%X' % funct), R[rd], R[rs], R[rt])
    return 'op%d 0x%08X' % (op, w)


def dis_range(blob, va, count, va_off=VA2FILE):
    """反汇编 count 条 (blob = ELF 文件内容, VA→FILE 用 va_off)"""
    out = []
    for i in range(count):
        a = va + i * 4
        o = a - va_off
        if o < 0 or o + 4 > len(blob):
            out.append((a, None, '<out of range>'))
            continue
        w = struct.unpack_from('<I', blob, o)[0]
        out.append((a, w, dis1(w, a)))
    return out


def mem_ops(blob, va_start, va_end, va_off=VA2FILE):
    """扫一段代码, 抽出所有「立即数内存访问」→ [(va, instr, op, rt, imm, rs)]"""
    out = []
    for a in range(va_start, va_end, 4):
        w = struct.unpack_from('<I', blob, a - va_off)[0]
        op = w >> 26
        if op in LOADS or op in STORES:
            out.append((a, dis1(w, a), (LOADS.get(op) or STORES[op]), (w >> 16) & 0x1F,
                        (w & 0xFFFF) - 0x10000 if (w & 0x8000) else (w & 0xFFFF), (w >> 21) & 0x1F))
        elif op in ALUI and op != 0x0F:
            out.append((a, dis1(w, a), ALUI[op], (w >> 16) & 0x1F,
                        (w & 0xFFFF) - 0x10000 if (w & 0x8000) else (w & 0xFFFF), (w >> 21) & 0x1F))
    return out
