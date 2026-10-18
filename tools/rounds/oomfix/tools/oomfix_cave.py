# -*- coding: utf-8 -*-
r"""oomfix_cave.py -- 【GR_OOMFIX】为 F2（NULL 检查 cave）选一个安全的落点。

READ-ONLY：只按 'rb' 打开基底 ISO / 参考 ISO。

做法
----
1. 从 ISO（ISO9660 目录，LBA 295）取出 SLUS_206.13。
2. 打印 PT_LOAD（含 flags）与 .symtab 符号区间。
3. 在**可执行 PT_LOAD 的文件覆盖区**里找全零 run（对齐 4，长度 >= MINLEN）。
4. 对每个候选做**可达性审计**：
     a) 全 .text 的 j / jal / 条件分支 / REGIMM 分支 / branch-likely 目标是否落进候选；
     b) 全 ELF（所有节）里是否有 32 位小端字面量等于候选区间内的地址；
     c) lui + (addiu|ori) 成对合成的地址是否落进候选；
     d) .symtab 里是否有符号的 [value, value+size) 与候选相交；
     e) 候选**前一条**指令是否是「函数收尾」（jr ra / j / beq zero,zero / nop / 0），
        用于排除「线性落入零区继续执行 nop」的假安全；
     f) 候选是否与既知占用区重叠（DBCS cave / 4 个闸门 / ZH cave block B / 其它挂点）。
5. 打分并打印排序结果；把 JSON 落盘。

usage:
  python oomfix_cave.py --iso <base.iso> [--min 0x40] [--top 20] [--json out.json]
"""
import argparse
import hashlib
import json
import os
import struct
import sys

SEC = 2048
ELF_NAME = 'SLUS_206.13'

# 既知占用 / 禁碰区间（VA 空间）：
#   DBCS cave 全区          : 0x416E00..0x417800   （iomanX 死代码被汉化 cave 覆盖）
#   ZH cave block B         : 0x565600..0x565B00
#   cave B / N1 / N2        : 0x411600..0x411700 / 0x407000..0x407100 / 0x408900..0x408A00
#   4 个 DBCS 闸门（单字）  : 0x416EE8 / 0x417160 / 0x41751C / 0x5656A4
#   DoWordWrap 尾部填充     : 0x21CC00..0x21CC10
FORBIDDEN = [
    (0x416E00, 0x417800, 'DBCS cave 全区（iomanX 死代码）'),
    (0x565600, 0x565B00, 'ZH cave block B'),
    (0x411600, 0x411700, 'cave B (0x411690)'),
    (0x407000, 0x407100, 'cave N1 (0x407078)'),
    (0x408900, 0x408A00, 'cave N2 (0x408928)'),
    (0x21CC00, 0x21CC10, 'DoWordWrap 尾部填充'),
    (0x21AC00, 0x21AE00, 'RSFont 被替换函数区'),
    (0x539100, 0x539300, '解压器本体（F1 站点所在函数）'),
    (0x51BE00, 0x51C000, '调用者 0x51BE10'),
]
GATES = [0x416EE8, 0x417160, 0x41751C, 0x5656A4]
# 本修复的 F1 站点（不能被 cave 覆盖）
F1_VA = 0x539174


def sha256_file(p, blk=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(blk), b''):
            h.update(b)
    return h.hexdigest()


def iso_find_file(f, want):
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    assert pvd[1:6] == b'CD001', '扇区 16 不是 ISO9660 PVD'
    root = pvd[156:156 + 34]
    rlba = struct.unpack_from('<I', root, 2)[0]
    rsize = struct.unpack_from('<I', root, 10)[0]
    data = b''
    for i in range((rsize + SEC - 1) // SEC):
        f.seek((rlba + i) * SEC)
        data += f.read(SEC)
    off = 0
    while off < len(data):
        ln = data[off]
        if ln == 0:
            off = (off // SEC + 1) * SEC
            continue
        rec = data[off:off + ln]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode('latin-1').upper()
        if name in (want + ';1', want):
            return ext, sz
        off += ln
    raise SystemExit('ISO 目录里找不到 %s' % want)


def read_elf(path):
    with open(path, 'rb') as f:
        lba, size = iso_find_file(f, ELF_NAME)
        f.seek(lba * SEC)
        d = f.read(size)
    assert d[:4] == b'\x7fELF'
    return d, lba, size


class Elf(object):
    def __init__(self, d):
        self.d = d
        e_phoff = struct.unpack_from('<I', d, 0x1C)[0]
        e_phentsize = struct.unpack_from('<H', d, 0x2A)[0]
        e_phnum = struct.unpack_from('<H', d, 0x2C)[0]
        self.ph = []
        for i in range(e_phnum):
            o = e_phoff + i * e_phentsize
            t, off, va, pa, fs, ms, fl, al = struct.unpack_from('<8I', d, o)
            self.ph.append(dict(type=t, off=off, va=va, pa=pa, filesz=fs, memsz=ms,
                                flags=fl, align=al))
        self.loads = [p for p in self.ph if p['type'] == 1]
        self.entry = struct.unpack_from('<I', d, 0x18)[0]

    def va2off(self, va):
        for p in self.loads:
            if p['filesz'] and p['va'] <= va < p['va'] + p['filesz']:
                return p['off'] + (va - p['va'])
        raise KeyError('VA 0x%08X 不在任何 PT_LOAD 的文件覆盖区' % va)

    def word(self, va):
        o = self.va2off(va)
        return struct.unpack_from('<I', self.d, o)[0]

    def syms(self):
        d = self.d
        e_shoff, = struct.unpack_from('<I', d, 0x20)
        e_shentsize, e_shnum = struct.unpack_from('<HH', d, 0x2E)
        shs = [struct.unpack_from('<10I', d, e_shoff + i * e_shentsize)
               for i in range(e_shnum)]
        symtab = next((s for s in shs if s[1] == 2), None)
        assert symtab, '没有 .symtab'
        so, ss, slink = symtab[4], symtab[5], symtab[6]
        strsh = shs[slink]
        sto = strsh[4]
        out = []

        def sname(off):
            e = d.index(b'\0', sto + off)
            return d[sto + off:e].decode('latin-1')
        for i in range(ss // 16):
            nm, val, size, info, other, shndx = struct.unpack_from('<IIIBBH', d, so + i * 16)
            out.append(dict(name=sname(nm), val=val, size=size, info=info, shndx=shndx))
        return out


def decode_target(va, w):
    """返回该指令的控制转移目标（VA），非转移返回 None。"""
    op = (w >> 26) & 0x3F
    if op in (2, 3):                                   # j / jal
        return ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
    if op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):  # REGIMM / 分支 / likely
        simm = w & 0xFFFF
        simm = simm - 0x10000 if simm & 0x8000 else simm
        return va + 4 + simm * 4
    if op == 0x11 and ((w >> 21) & 0x1F) == 8:         # COP1 bc1f/bc1t
        simm = w & 0xFFFF
        simm = simm - 0x10000 if simm & 0x8000 else simm
        return va + 4 + simm * 4
    return None


def reloc_offsets(data):
    """解析 .relmain（SHT_REL，type=9）的 r_offset 列表。"""
    e_shoff, = struct.unpack_from('<I', data, 0x20)
    e_shentsize, e_shnum = struct.unpack_from('<HH', data, 0x2E)
    out = []
    for i in range(e_shnum):
        sh = struct.unpack_from('<10I', data, e_shoff + i * e_shentsize)
        if sh[1] != 9:
            continue
        off, sz = sh[4], sh[5]
        for k in range(sz // 8):
            r_off, r_info = struct.unpack_from('<II', data, off + k * 8)
            out.append(r_off)
    return out


def func_ranges(elf):
    """由 .symtab 的 FUNC 符号（shndx=4 的 main 段）给出**真代码**区间。"""
    out = []
    for s in elf.syms():
        if (s['info'] & 0xF) == 2 and s['shndx'] == 4 and s['size']:
            out.append((s['val'], s['val'] + s['size']))
    out.sort()
    return out


def audit(elf, lo, hi, data, seg, text_lo, text_hi, franges, reloffs):
    """对候选 [lo,hi) 做可达性审计。返回 report dict。"""
    rep = dict(lo='0x%08X' % lo, hi='0x%08X' % hi, size=hi - lo)
    # a) 控制转移 —— 只在**有 FUNC 符号覆盖**的地址上扫，避开把 .rodata/.data 当代码的假命中
    refs = []
    for (flo, fhi) in franges:
        for va in range(max(flo, text_lo), min(fhi, text_hi) - 4, 4):
            w = elf.word(va)
            t = decode_target(va, w)
            if t is not None and lo <= t < hi:
                op = (w >> 26) & 0x3F
                kind = 'jal' if op == 3 else ('j' if op == 2 else 'branch')
                refs.append(dict(kind=kind, site='0x%08X' % va, target='0x%08X' % t,
                                 word='0x%08X' % w))
    rep['ctrl_refs'] = refs
    # a2) 全段线性扫描（含把数据当代码的假命中）—— 只统计，作为风险参考
    raw = 0
    for va in range(text_lo, text_hi - 4, 4):
        w = elf.word(va)
        t = decode_target(va, w)
        if t is not None and lo <= t < hi:
            raw += 1
    rep['ctrl_refs_raw_linear'] = raw
    # b) 字面量 32 位指针（只扫**装载段**的文件范围）
    lits = []
    o0, o1 = seg['off'], seg['off'] + seg['filesz']
    for o in range(o0, o1 - 4, 4):
        v = struct.unpack_from('<I', data, o)[0]
        if lo <= v < hi:
            lits.append(o)
    rep['literal_word_offsets'] = ['0x%X' % o for o in lits[:40]]
    rep['literal_word_count'] = len(lits)
    # c) lui + addiu/ori 合成地址（同样只扫 FUNC 覆盖的地址）
    syn = []
    lui = {}
    for (flo, fhi) in franges:
        for va in range(max(flo, text_lo), min(fhi, text_hi) - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            rs, rt = (w >> 21) & 0x1F, (w >> 16) & 0x1F
            if op == 0x0F:
                lui[rt] = (va, w & 0xFFFF)
            elif op in (0x09, 0x0D) and rs in lui:
                (lva, hi16) = lui[rs]
                if va - lva > 0x40:
                    continue
                imm = w & 0xFFFF
                if op == 0x09:                          # addiu：符号扩展相加
                    simm = imm - 0x10000 if imm & 0x8000 else imm
                    addr = ((hi16 << 16) + simm) & 0xFFFFFFFF
                else:                                   # ori：零扩展相或
                    addr = ((hi16 << 16) | imm) & 0xFFFFFFFF
                if lo <= addr < hi:
                    syn.append(dict(lui='0x%08X' % lva, use='0x%08X' % va, addr='0x%08X' % addr))
    rep['lui_synth'] = syn
    # c2) .relmain 重定位目标（数据侧的指针修正）
    rl = [o for o in reloffs if lo <= o < hi]
    rep['reloc_targets_in_region'] = ['0x%08X' % o for o in rl[:40]]
    rep['reloc_target_count'] = len(rl)
    # d) 符号
    shits = []
    for s in elf.syms():
        if s['val'] and s['size']:
            if s['val'] < hi and s['val'] + s['size'] > lo:
                shits.append(dict(val='0x%08X' % s['val'], size=s['size'], name=s['name']))
    rep['symbol_hits'] = shits
    # e) 前一条指令是否「收尾」
    prev = None
    if lo - 8 >= text_lo:
        prev = ('0x%08X' % elf.word(lo - 8), '0x%08X' % elf.word(lo - 4))
    rep['prev2'] = prev
    nxt = '0x%08X' % elf.word(hi) if hi + 4 <= text_hi else None
    rep['next_word'] = nxt
    # f) 禁碰区间
    rep['forbidden_overlap'] = [dict(lo='0x%08X' % a, hi='0x%08X' % b, why=w)
                                for (a, b, w) in FORBIDDEN if a < hi and lo < b]
    rep['gate_hits'] = ['0x%08X' % g for g in GATES if lo <= g < hi]
    rep['f1_in_region'] = bool(lo <= F1_VA < hi)
    rep['ok'] = (not refs and not lits and not syn and not shits and not rl
                 and not rep['forbidden_overlap'] and not rep['gate_hits']
                 and not rep['f1_in_region'])
    return rep


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--min', default='0x40', help='最小零 run 长度（十六进制）')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    minlen = int(a.min, 16)

    data, lba, size = read_elf(a.iso)
    elf = Elf(data)
    print('ISO    : %s' % a.iso)
    print('  sha256=%s  bytes=%d' % (sha256_file(a.iso), os.path.getsize(a.iso)))
    print('ELF    : LBA %d, %d B, sha256=%s' % (lba, size, hashlib.sha256(data).hexdigest()))
    print('entry  : 0x%08X' % elf.entry)
    for p in elf.ph:
        print('  PH type=%d off=0x%06X va=0x%08X filesz=0x%07X memsz=0x%07X flags=0x%X'
              % (p['type'], p['off'], p['va'], p['filesz'], p['memsz'], p['flags']))
    seg = elf.loads[0]
    text_lo, text_hi = seg['va'], seg['va'] + seg['filesz']
    print('  exec PT_LOAD 覆盖 VA 0x%08X..0x%08X（文件 off 0x%06X..0x%06X）'
          % (text_lo, text_hi, seg['off'], seg['off'] + seg['filesz']))

    # 全零 run
    blob = data[seg['off']:seg['off'] + seg['filesz']]
    runs = []
    i = 0
    n = len(blob)
    while i < n:
        if blob[i] == 0:
            j = i
            while j < n and blob[j] == 0:
                j += 1
            if j - i >= minlen:
                runs.append((text_lo + i, text_lo + j))
            i = j
        else:
            i += 1
    print('零 run（>= 0x%X，对齐后）: %d 个' % (minlen, len(runs)))

    franges = func_ranges(elf)
    print('FUNC 符号区间: %d 个（覆盖 %d B）'
          % (len(franges), sum(b - a for (a, b) in franges)))
    reloffs = reloc_offsets(data)
    print('.relmain 重定位条目: %d' % len(reloffs))

    reps = []
    for (lo, hi) in runs:
        # 对齐到 4
        lo4 = (lo + 3) & ~3
        hi4 = hi & ~3
        if hi4 - lo4 < minlen:
            continue
        reps.append(audit(elf, lo4, hi4, data, seg, text_lo, text_hi, franges, reloffs))

    oks = [r for r in reps if r['ok']]
    oks.sort(key=lambda r: -(r['size']))
    print('\n===== 通过审计的候选（%d 个），按长度降序 =====' % len(oks))
    for r in oks[:a.top]:
        print('  0x%s..0x%s  %5d B  prev2=%s next=%s'
              % (r['lo'][2:], r['hi'][2:], r['size'], r['prev2'], r['next_word']))
    print('\n===== 未通过审计的候选（前 %d，按长度降序，看拒绝原因）=====' % a.top)
    bad = sorted([r for r in reps if not r['ok']], key=lambda r: -r['size'])
    for r in bad[:a.top]:
        why = []
        if r['ctrl_refs']:
            why.append('ctrl=%d' % len(r['ctrl_refs']))
        if r['literal_word_count']:
            why.append('lit=%d' % r['literal_word_count'])
        if r['lui_synth']:
            why.append('lui=%d' % len(r['lui_synth']))
        if r['symbol_hits']:
            why.append('sym=%d' % len(r['symbol_hits']))
        if r['forbidden_overlap']:
            why.append('forbid=%s' % ','.join(o['why'] for o in r['forbidden_overlap']))
        if r['gate_hits']:
            why.append('gate')
        print('  0x%s..0x%s  %5d B  %s' % (r['lo'][2:], r['hi'][2:], r['size'], ' '.join(why)))

    if a.json:
        json.dump(dict(iso=a.iso, elf_lba=lba, elf_bytes=size,
                       elf_sha256=hashlib.sha256(data).hexdigest(),
                       segs=[dict(va='0x%08X' % p['va'], off='0x%06X' % p['off'],
                                  filesz='0x%07X' % p['filesz'], memsz='0x%07X' % p['memsz'],
                                  flags=p['flags']) for p in elf.ph],
                       zero_runs=len(runs), audited=reps, passed=len(oks)),
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n[json] %s' % a.json)
    return 0 if oks else 1


if __name__ == '__main__':
    sys.exit(main())
