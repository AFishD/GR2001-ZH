# -*- coding: utf-8 -*-
r"""s5_cave.py (round44 实验) — 决定性: 现役盘 ELF 的 cctc cave 里到底有没有"行相位(PHI)表"?

只读 (LBA 295 + 0x80 的 ELF 段)。判据:
  ① 把 PHI 表可能存在的几种编码 (u8/u16/u32, PHI 与 16*PHI) 在全 ELF 里精确搜索;
  ② 把 cave 区 (0x417050..0x417150) 与它前后 0x1000 字节打印出来, 看有无表;
  ③ 反汇编 cave 前 64 条指令 (只解出"能确定的"指令, 其余打 .word), 看 U0/V0 怎么算。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LOG = []


def log(s):
    print(s)
    LOG.append(s)


PHI = [6, 6, 6, 6, 12, 12, 12, 12, 18, 18, 18, 18, 24, 30, 30, 30, 30, 36, 36, 2, 2, 2, 2, 2, 0]
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    with open(iso, 'rb') as f:
        f.seek(elf_off(0x100000))
        head = f.read(4)
        assert head == b'\x7fELF', head
        f.seek(elf_off(0x417050 - 0x400))
        blob = f.read(0x400 + 0x140 + 0x400)          # cave 前后各 0x400
        cave_va0 = 0x417050 - 0x400
    log('[elf] %s  ELF@LBA %d 读入 0x%X..0x%X' % (os.path.relpath(iso, REPO), ELF_LBA,
                                                  cave_va0, cave_va0 + len(blob)))

    # ① 全 ELF 搜 PHI 表的各种编码 (只在 ELF 段范围内搜, 大小 = 文件大小)
    with open(iso, 'rb') as f:
        f.seek(0, os.SEEK_END)
        isosize = f.tell()
    with open(iso, 'rb') as f:
        f.seek(elf_off(0x100000))
        elf = f.read(isosize - elf_off(0x100000))
    log('[elf] ELF 段 %d 字节 (0x%X)' % (len(elf), len(elf)))
    pats = {
        'u8  PHI': bytes(PHI),
        'u8  PHI(24)': bytes(PHI[:24]),
        'u16 PHI': b''.join(struct.pack('<H', v) for v in PHI),
        'u32 PHI': b''.join(struct.pack('<I', v) for v in PHI),
        'u16 16*PHI': b''.join(struct.pack('<H', 16 * v) for v in PHI),
        'u32 16*PHI': b''.join(struct.pack('<I', 16 * v) for v in PHI),
        'u8  16*PHI': bytes(16 * v for v in PHI if 16 * v < 256),
    }
    for nm, pat in pats.items():
        hits, i = [], elf.find(pat)
        while i >= 0 and len(hits) < 8:
            hits.append(0x100000 + i)
            i = elf.find(pat, i + 1)
        log('[phi] %-12s len=%2d 命中 %s' % (nm, len(pat),
            ' '.join('VA 0x%06X' % h for h in hits) if hits else '**无**'))

    # ② cave 前后字节
    log('[cave] 0x417050..0x417140 原始字节 (每行 16B):')
    c0 = 0x400
    for r in range(0, 0x100, 16):
        va = cave_va0 + c0 + r
        log('  0x%06X  %s' % (va, blob[c0 + r:c0 + r + 16].hex(' ')))

    # ③ 逐指令打印关键立即数 (简化: 只标出 addiu/ori/lui/sll/srl/mult 等, 其余打 word)
    def dis(w, va):
        op = w >> 26
        rs, rt, rd = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        sa, fn = (w >> 6) & 31, w & 63
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 0 and fn == 0:
            return 'nop'
        if op == 0x0F:
            return 'lui   r%d, 0x%X' % (rt, imm)
        if op == 0x09:
            return 'addiu r%d, r%d, %d' % (rt, rs, simm)
        if op == 0x0D:
            return 'ori   r%d, r%d, 0x%X' % (rt, rs, imm)
        if op == 0x0C:
            return 'andi  r%d, r%d, 0x%X' % (rt, rs, imm)
        if op == 0x00:
            names = {0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x18: 'mult', 0x1A: 'div',
                     0x21: 'addu', 0x23: 'subu', 0x2A: 'slt', 0x08: 'jr', 0x09: 'jalr',
                     0x25: 'or', 0x24: 'and', 0x20: 'add'}
            if fn == 0x08:
                return 'jr    r%d' % rs
            if fn in (0x00, 0x02, 0x03):
                return '%s   r%d, r%d, %d' % (names[fn], rd, rt, sa)
            if fn in names:
                return '%-5s r%d, r%d, r%d' % (names[fn], rd, rs, rt)
        if op == 0x03:
            return 'jal   0x%X' % (((va + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
        if op == 0x02:
            return 'j     0x%X' % (((va + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
        if op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x2B):
            nm = {0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x2B: 'sw'}[op]
            return '%-5s r%d, %d(r%d)' % (nm, rt, simm, rs)
        if op in (0x28, 0x29, 0x2A):
            nm = {0x28: 'sb', 0x29: 'sh', 0x2A: 'sw'}[op]
            return '%-5s r%d, %d(r%d)' % (nm, rt, simm, rs)
        if op in (0x04, 0x05, 0x06, 0x07):
            nm = {0x04: 'beq', 0x05: 'bne', 0x06: 'blez', 0x07: 'bgtz'}[op]
            return '%-5s r%d, r%d, 0x%X' % (nm, rs, rt, va + 4 + (simm << 2))
        if op == 0x01:
            return 'regimm/bltz (rt=%d) -> 0x%X' % (rt, va + 4 + (simm << 2))
        return '.word 0x%08X' % w
    log('[cave] 反汇编 0x417050..0x417100:')
    o = 0x400
    for _ in range(44):
        va = cave_va0 + o
        w = struct.unpack_from('<I', blob, o)[0]
        log('  0x%06X  %08X  %s' % (va, w, dis(w, va)))
        o += 4
    with open(os.path.join(HERE, 's5_cave.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
