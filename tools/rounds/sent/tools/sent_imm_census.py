# -*- coding: utf-8 -*-
r"""sent_imm_census.py —— 全 ELF「0xB1 / 0xB5 硬编码消费者」穷举普查（只读）。

目的（REPORT_SENTINEL.md §6-C2 / §9.7 的收口）：
  除了 `addiu rX,zero,0xFFB1|0xFFB5`（已知 10 处 = DrawString 8 + CharWidth 2）之外，
  **还有没有别的地方对这两个字节做硬编码比较**？逐类穷举：

  A. 单指令立即数普查：**所有** I 型指令里 imm16 ∈ {0x00B1,0x00B5,0xFFB1,0xFFB5}
     （不看 opcode —— addiu/addi/ori/xori/andi/slti/sltiu/lui/…，一律列出后人工分类）
     · 其中 `sltiu/slti` 命中 = **区间边界**（如 gate `sltiu t,r,0xB1` ⇒ r<0xB1），
       语义上"0xB1 及以上走另一条路"，不是相等比较 —— 单列并标注。
  B. 32 位常量拼装：`lui rX,hi` 紧跟 `ori/addiu rX,rX,lo`，拼出
     0x000000B1 / 0x000000B5 / 0xFFFFFFB1 / 0xFFFFFFB5（含 0x0000B1xx 之类的高位形态）。
  C. 数据侧常量：非 .text 区（.rodata/.data）里 4 字节对齐出现
     0x000000B1 / 0x000000B5 / 0xFFFFFFB1 / 0xFFFFFFB5 的次数与位置，
     并反查"有没有代码用 lui+lo 的地址把它取进来"（address_materialization 表）。
  D. 已知形态的**交叉验证**：DrawString(0x219A70) / CharWidth(0x21AD10) /
     4 个 gate 站点，逐个打印原始字与反汇编，防止口径漂移。

用法：
  python sent_imm_census.py <elf-file> [--iso <iso>] [--tag NAME] [--out OUTFILE]
  · <elf-file> 可以是磁盘上的 ELF 文件；也可以给 `--iso`，此时按 ISO = VA − 0x6C780
    从 ISO 里就地读（ZH113b 的 ELF 在盘上，不落地解包）。
"""
import argparse
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))

import importlib.util                                                     # noqa: E402
_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

ISO_OF_VA = 0x6C780                     # 与 sent_lib 同口径（REPORT_TEXT_OVERFLOW §3.1）
ICON_IMMS = (0x00B1, 0x00B5, 0xFFB1, 0xFFB5)
SIGNED_OF = {0x00B1: 0xFFB1, 0xFFB1: 0xFFB1, 0x00B5: 0xFFB5, 0xFFB5: 0xFFB5}
UNSIGNED_OF = {0x00B1: 0x00B1, 0xFFB1: 0x00B1, 0x00B5: 0x00B5, 0xFFB5: 0x00B5}
BYTE_OF = {0x00B1: 0xB1, 0xFFB1: 0xB1, 0x00B5: 0xB5, 0xFFB5: 0xB5}

DRAWSTRING = (0x219A70, 0x219E00)
CHARWIDTH = (0x21AD10, 0x21AE60)
GATE_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)

OPNAME = {0x00: 'SPECIAL', 0x01: 'REGIMM', 0x02: 'j', 0x03: 'jal', 0x04: 'beq', 0x05: 'bne',
          0x06: 'blez', 0x07: 'bgtz', 0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu',
          0x0C: 'andi', 0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui', 0x10: 'cop0', 0x11: 'cop1',
          0x12: 'cop2', 0x14: 'beql', 0x15: 'bnel', 0x16: 'blezl', 0x17: 'bgtzl',
          0x18: 'daddi', 0x19: 'daddiu', 0x1A: 'ldl', 0x1B: 'ldr', 0x1C: 'MMI', 0x1D: 'ldai',
          0x1E: 'lqi', 0x1F: 'SPECIAL3', 0x20: 'lb', 0x21: 'lh', 0x22: 'lwl', 0x23: 'lw',
          0x24: 'lbu', 0x25: 'lhu', 0x26: 'lwr', 0x27: 'lwu', 0x28: 'sb', 0x29: 'sh',
          0x2A: 'swl', 0x2B: 'sw', 0x2C: 'sdl', 0x2D: 'sdr', 0x2E: 'swr', 0x2F: 'cache',
          0x30: 'll', 0x31: 'lwc1', 0x32: 'lwc2', 0x33: 'pref', 0x34: 'lld', 0x35: 'ldc1',
          0x36: 'ldc2', 0x37: 'ld', 0x38: 'sc', 0x39: 'swc1', 0x3A: 'swc2', 0x3B: 'sq',
          0x3C: 'scd', 0x3D: 'sdc1', 0x3E: 'sdc2', 0x3F: 'sd'}

# 「会拿立即数当被比较常量」的 opcode（相等比较 / 位掩码 / 区间边界）
CMP_OPS = (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x18, 0x19)
# 「立即数是一个 offset/size」的 opcode（绝不可能当成 0xB1 常量比较）
OFFSET_OPS = set(range(0x20, 0x40)) | {0x1A, 0x1B, 0x1E, 0x1F}


class Src:
    """ELF 数据源：磁盘文件 或 ISO 内就地读（只读）。

    统一对外提供 `read_va(va,n)`：ELF 文件按 PT_LOAD(off,va) 映射；
    ISO 里 ELF 基址靠**魔法扫描**定位（`VA − ISO = 0x6C780` 是**代码区**的口径，
    而 ELF 头在它前面 0x80 = 第一个 PT_LOAD 的 `off`，见 REPORT_TEXT_OVERFLOW §3.1）。
    """
    ELF_VA0 = 0x100000
    HINT = ELF_VA0 - ISO_OF_VA              # 0x93880，ELF 头的**上界**提示

    def __init__(self, elf_file, iso=None):
        if iso:
            self.d = None
            self.f = open(iso, 'rb')
            self.iso = iso
            self.elf_file = None
            self.base = self._find_elf(iso)
        else:
            with open(elf_file, 'rb') as f:
                self.d = f.read()
            self.f = None
            self.iso = None
            self.elf_file = elf_file
            self.base = 0
        self.segs = self._phdrs()

    def _find_elf(self, iso):
        """在 0x93880 附近（含往前 0x400）扫 ELF 魔法，返回 ELF 头在 ISO 里的偏移。"""
        for off in range(self.HINT, self.HINT - 0x400, -1):
            self.f.seek(off)
            if self.f.read(4) == b'\x7fELF':
                print('# [Src] ISO %s : ELF 魔法在 0x%X（提示上界 0x%X，差 %d B）'
                      % (os.path.basename(iso), off, self.HINT, self.HINT - off))
                return off
        raise AssertionError('在 0x%X 往前 0x400 内没找到 ELF 魔法' % self.HINT)

    def pread(self, off, n):
        if self.f is not None:
            self.f.seek(off)
            return self.f.read(n)
        return self.d[off:off + n]

    def _phdrs(self):
        hdr = self.pread(self.base, 0x40)
        assert hdr[:4] == b'\x7fELF', '不是 ELF（头偏移 0x%X，读到 %s）' % (self.base, hdr[:4])
        e_phoff = struct.unpack_from('<I', hdr, 0x1C)[0]
        e_phentsize = struct.unpack_from('<H', hdr, 0x2A)[0]
        e_phnum = struct.unpack_from('<H', hdr, 0x2C)[0]
        self.entry = struct.unpack_from('<I', hdr, 0x18)[0]
        segs = []
        for i in range(e_phnum):
            o = self.base + e_phoff + i * e_phentsize
            t, off, va, pa, fs, ms, fl, al = struct.unpack('<8I', self.pread(o, 32))
            segs.append(dict(type=t, off=off, va=va, pa=pa, filesz=fs, memsz=ms, flags=fl))
        return segs

    def read_va(self, va, n):
        for s in self.segs:
            if s['type'] == 1 and s['filesz'] and s['va'] <= va < s['va'] + s['filesz']:
                off = self.base + s['off'] + (va - s['va'])
                return self.pread(off, n)
        raise KeyError('VA 0x%08X 不在任何 PT_LOAD 内' % va)

    def word(self, va):
        return struct.unpack('<I', self.read_va(va, 4))[0]

    def close(self):
        if self.f is not None:
            self.f.close()


def i_type_sites(src, va0, size):
    """扫 [va0, va0+size)：返回所有 imm16 ∈ ICON_IMMS 的指令。"""
    out = []
    for k in range(0, size - 3, 4):
        w = src.word(va0 + k)
        imm = w & 0xFFFF
        if imm in ICON_IMMS:
            op = (w >> 26) & 0x3F
            va = va0 + k
            out.append(dict(va=va, iso_off=va - ISO_OF_VA, word=w, op=op,
                            opname=OPNAME.get(op, 'op%02X' % op),
                            rs=(w >> 21) & 0x1F, rt=(w >> 16) & 0x1F, imm=imm,
                            byte=BYTE_OF[imm],
                            kind=('cmp_imm' if op in CMP_OPS else
                                  ('offset_imm' if op in OFFSET_OPS else 'other')),
                            dis=CD.dis(w, va)))
    return out


def lui_pairs(src, va0, size):
    """找 `lui rX,hi` + 后续 ±3 条内 `ori/addiu rX,rX,lo`，拼出 32 位常量；只留相关值。"""
    words = []
    for k in range(0, size - 3, 4):
        va = va0 + k
        w = src.word(va)
        words.append((va, w))
    out = []
    for idx, (va, w) in enumerate(words):
        if ((w >> 26) & 0x3F) != 0x0F:                       # lui
            continue
        hi = w & 0xFFFF
        rt = (w >> 16) & 0x1F
        for j in range(idx + 1, min(idx + 4, len(words))):
            va2, w2 = words[j]
            op2 = (w2 >> 26) & 0x3F
            if op2 in (0x0D, 0x09, 0x19) and ((w2 >> 21) & 0x1F) == rt \
               and ((w2 >> 16) & 0x1F) == rt:
                lo = w2 & 0xFFFF
                val = ((hi << 16) | lo) & 0xFFFFFFFF
                if op2 in (0x09, 0x19):                       # addiu ⇒ 符号扩展低半
                    val = ((hi << 16) + struct.unpack('<i', struct.pack('<I', lo << 16))[0]) \
                        & 0xFFFFFFFF
                if val in (0x000000B1, 0x000000B5, 0xFFFFFFB1, 0xFFFFFFB5, 0x0000B100,
                           0x0000B500, 0xB1000000, 0xB5000000, 0xFFFFB1FF, 0xFFFFB5FF):
                    out.append(dict(va=va, va_lo=va2, value='0x%08X' % val,
                                    hi='0x%04X' % hi, lo='0x%04X' % lo, rt=rt,
                                    dis=CD.dis(w, va) + ' ; ' + CD.dis(w2, va2)))
                break
            if ((w2 >> 26) & 0x3F) in (0x0F,) and ((w2 >> 16) & 0x1F) == rt:
                break
    return out


def data_words(src, segs, text_lo, text_hi):
    """非 .text 区 4 字节对齐的 0x000000B1/B5/0xFFFFFFB1/B5 常量。"""
    out = []
    TARGET = (0x000000B1, 0x000000B5, 0xFFFFFFB1, 0xFFFFFFB5)
    for s in segs:
        if s['type'] != 1 or not s['filesz']:
            continue
        lo, hi = s['va'], s['va'] + s['filesz']
        for va in range(lo, hi - 3, 4):
            if text_lo <= va < text_hi:
                continue
            w = src.word(va)
            if w in TARGET:
                out.append(dict(va=va, iso_off=va - ISO_OF_VA, value='0x%08X' % w))
    return out


def addrs_materialized(src, va0, size):
    """所有 `lui rX,hi` + `addiu/ori rX,rX,lo` 拼出的**基址候选**（用于反查数据常量引用）。"""
    words = []
    for k in range(0, size - 3, 4):
        va = va0 + k
        w = src.word(va)
        words.append((va, w))
    res = {}
    for idx, (va, w) in enumerate(words):
        if ((w >> 26) & 0x3F) != 0x0F:
            continue
        hi = w & 0xFFFF
        rt = (w >> 16) & 0x1F
        if hi == 0:
            continue
        for j in range(idx + 1, min(idx + 5, len(words))):
            va2, w2 = words[j]
            op2 = (w2 >> 26) & 0x3F
            rs2 = (w2 >> 21) & 0x1F
            if rs2 != rt:
                break
            if op2 in (0x09, 0x0D) and ((w2 >> 16) & 0x1F) == rt:
                lo = w2 & 0xFFFF
                if op2 == 0x09:
                    lo = struct.unpack('<i', struct.pack('<I', lo << 16))[0] >> 16
                val = ((hi << 16) + lo) & 0xFFFFFFFF
                res.setdefault(val, []).append(va)
            if op2 in (0x0F, 0x23, 0x2B):
                break
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('elf')
    ap.add_argument('--iso', default=None)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    src = Src(a.elf, a.iso)
    entry, segs = src.entry, src.segs
    tag = a.tag or os.path.basename(a.elf)
    buf = io.StringIO()

    def P(*x):
        print(*x)
        buf.write(' '.join(str(y) for y in x) + '\n')

    P('#' * 90)
    P('# 全 ELF 0xB1/0xB5 硬编码消费者普查 —— %s' % tag)
    P('# 源 = %s%s' % (a.iso or a.elf, '（ISO 内就地读，ISO = VA − 0x%X）' % ISO_OF_VA
                        if a.iso else ''))
    P('# entry=0x%08X  PT_LOAD %d 个：' % (entry, len(segs)))
    for s in segs:
        P('#   type=%d off=0x%06X va=0x%08X filesz=0x%07X (%d B) flags=0x%X'
          % (s['type'], s['off'], s['va'], s['filesz'], s['filesz'], s['flags']))
    loads = [s for s in segs if s['type'] == 1 and s['filesz']]
    text_lo = min(s['va'] for s in loads)
    text_hi = max(s['va'] + s['filesz'] for s in loads)

    sites = []
    for s in loads:
        sites += i_type_sites(src, s['va'], s['filesz'])
    P('')
    P('=' * 90)
    P('A. 单指令立即数 imm16 ∈ {0x00B1,0x00B5,0xFFB1,0xFFB5}：**%d 处**' % len(sites))
    P('=' * 90)
    P('%-12s %-10s %-8s %-6s %-6s %s' % ('VA', 'ISO', 'op', 'rt', 'kind', 'disasm / word'))
    for s in sorted(sites, key=lambda z: z['va']):
        P('0x%08X  0x%07X  %-8s r%-5d %-10s 0x%08X  %s'
          % (s['va'], s['iso_off'], s['opname'], s['rt'], s['kind'], s['word'], s['dis']))

    by_kind = {}
    for s in sites:
        by_kind.setdefault(s['kind'], []).append(s)
    P('')
    P('  分类计数：%s' % {k: len(v) for k, v in sorted(by_kind.items())})

    # ── 已知 10 处（addiu rX,zero,imm）＋ CharWidth 2 处 ──
    mat = [s for s in sites if s['op'] in (0x09, 0x08) and s['rs'] == 0]
    P('  其中 `addiu/addi rX,zero,imm`（= 把常量装进寄存器，最典型的"硬编码比较"形态）：%d 处'
      % len(mat))
    ds = [s for s in mat if DRAWSTRING[0] <= s['va'] < DRAWSTRING[1]]
    cw = [s for s in mat if CHARWIDTH[0] <= s['va'] < CHARWIDTH[1]]
    P('    · DrawString [0x%X,0x%X)：%d 处' % (DRAWSTRING + (len(ds),)))
    P('    · CharWidth  [0x%X,0x%X)：%d 处' % (CHARWIDTH + (len(cw),)))
    oth = [s for s in mat if s not in ds and s not in cw]
    P('    · 其它：%d 处 %s' % (len(oth), ['0x%X' % s['va'] for s in oth]))

    # ── 其它形态：ori/andi/slti/sltiu/lui ──
    for opc, nm in ((0x0D, 'ori'), (0x0C, 'andi'), (0x0E, 'xori'), (0x0A, 'slti'),
                    (0x0B, 'sltiu'), (0x0F, 'lui')):
        sub = [s for s in sites if s['op'] == opc]
        if sub:
            P('  `%s` 形态 %d 处：' % (nm, len(sub)))
            for s in sub:
                P('    0x%08X (ISO 0x%07X) 0x%08X  %s' % (s['va'], s['iso_off'], s['word'],
                                                          s['dis']))

    P('')
    P('=' * 90)
    P('B. lui+ori/addiu 拼出的 32 位常量（0x…B1/B5 及其高位形态）')
    P('=' * 90)
    lp = []
    for s in loads:
        lp += lui_pairs(src, s['va'], s['filesz'])
    if not lp:
        P('  **0 处**')
    for s in lp:
        P('  0x%08X → %s   %s' % (s['va'], s['value'], s['dis']))

    P('')
    P('=' * 90)
    P('C. 非 .text 区（.rodata/.data）里 4 字节对齐的 0x000000B1/B5、0xFFFFFFB1/B5')
    P('=' * 90)
    dw = data_words(src, segs, text_lo, text_hi)
    P('  命中 %d 处：' % len(dw))
    for s in dw:
        P('    0x%08X (ISO 0x%07X) = %s' % (s['va'], s['iso_off'], s['value']))
    amap = {}
    for s in loads:
        for k, v in addrs_materialized(src, s['va'], s['filesz']).items():
            amap.setdefault(k, []).extend(v)
    ref = [(s, amap.get(s['va'])) for s in dw]
    hit = [(s, r) for (s, r) in ref if r]
    P('  其中"有代码用 lui+lo 把该地址取进来"的：%d 处' % len(hit))
    for s, r in hit:
        P('    0x%08X ← %s' % (s['va'], ['0x%X' % x for x in r]))

    P('')
    P('=' * 90)
    P('D. 已知形态逐个交叉验证（原始字 + 反汇编）')
    P('=' * 90)
    for va in GATE_SITES:
        try:
            w = src.word(va)
            P('  gate 候选 0x%08X (ISO 0x%07X) = 0x%08X   %s'
              % (va, va - ISO_OF_VA, w, CD.dis(w, va)))
        except Exception as e:                                            # noqa: BLE001
            P('  gate 候选 0x%08X 读取失败 %s' % (va, e))

    # DrawString / CharWidth 全区间反汇编里含 0xB1/0xB5 立即数的行
    P('')
    P('  · 全 ELF 里"visited by disasm"再确认：把已知 10 处逐条打印（含所在函数判定）')
    for s in sorted(sites, key=lambda z: z['va']):
        if s['kind'] == 'cmp_imm' and s['op'] in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):
            P('    0x%08X 0x%08X %-8s %s' % (s['va'], s['word'], s['opname'], s['dis']))

    src.close()
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(buf.getvalue())
        print('[out] %s' % a.out)
    # JSON 旁挂
    if a.out:
        jp = os.path.splitext(a.out)[0] + '.json'
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(dict(tag=tag, src=a.iso or a.elf, entry=entry, segs=segs,
                           i_type_sites=sites, lui_pairs=lp, data_words=dw,
                           data_words_referenced=[dict(s, refs=r) for s, r in hit],
                           n_total=len(sites)),
                      f, ensure_ascii=False, indent=1)
        print('[out] %s' % jp)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
