# -*- coding: utf-8 -*-
r"""lay_census.py —— 【GR_LAYOUT】A.1 残存几何常量普查 + A 线/B 线/原盘逐字差异（只读）。

用法
----
  # 立即数普查（addiu/sltiu/slti/ori/andi/lui 里出现的几何常量）
  python lay_census.py census <elf> [-o out.txt]

  # 两 ELF 逐字差异（按 R5900 反汇编打印）
  python lay_census.py diff <elfA> <elfB> [-o out.txt]

  # 指定区间的"几何相关站点"总表
  python lay_census.py sites <elf> [-o out.txt]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lay_dis import Elf, dis_r5900, dis_mips32  # noqa: E402

# 与"格子/行/列/槽/UV/步进"可能有关的常量（十进制）
GEOM = {
    2: 'V0+Y0 增量 / 副包容量 / 步长 2',
    3: 'SKIP_ROWS / V0 偏移',
    10: '记录步长 /10',
    12: 'row>=12 阈值 / div 12',
    16: '格宽/格高 (CW=CH=16)',
    18: 'V1 偏移 = Y0+16',
    19: 'V1 偏移 = Y0+16 (B 线)',
    20: '图标宽/记录步长 20',
    32: '空格 / ATLAS 段行数',
    62: '旧 NCOL',
    63: 'ASCII 矩形数 / 段数据行数',
    64: '新 NCOL (B 线)',
    94: 'trail 区间 (PAIR_STRIDE)',
    95: '94+1',
    104: 'DrawLetters 行数',
    128: '签名字节 / 上限',
    224: '0xE0 = 单字节码位数',
    255: '0xFF 上界',
    512: '旧图集高',
    640: '旧图集高 (F364)',
    644: '新图集高 (2400)',
    1024: '图集宽 / StringWidth 守卫',
    1280: '主顶点包容量',
    1736: '现役槽上界+1 (LIVE_HI+1)',
    1872: 'r84 槽上界+1',
    2344: '保留槽上界',
    2350: 'slot_space',
    2368: 'cells (37*64)',
    2432: 'cells (38*64)',
    329744: 'px_size (h=644)',
}


def iter_text(elf):
    va0, _o, fsz = elf.text()
    for va in range(va0, va0 + fsz - 4, 4):
        yield va, elf.word(va)


def load_imm(w):
    """返回 (kind, rd/rt, imm) —— 只认"把立即数装进寄存器"的形态。"""
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    if op == 0x09 and rs == 0:      # addiu rt,zero,imm
        return ('addiu', rt, simm, imm)
    if op == 0x0D and rs == 0:      # ori rt,zero,imm
        return ('ori', rt, imm, imm)
    if op == 0x0F and rs == 0:      # lui rt,imm
        return ('lui', rt, imm, imm)
    return None


def census(elf, out):
    out.write('# %s\n' % elf_path)
    out.write('# text seg = %s\n' % (elf.text(),))
    out.write('# ── A.1 常量普查：把立即数装进寄存器（addiu/ori/lui rd,zero,K）──\n')
    hits = {}
    for va, w in iter_text(elf):
        r = load_imm(w)
        if not r:
            continue
        kind, reg, sval, uval = r
        if kind == 'addiu' and sval in GEOM:
            hits.setdefault(sval, []).append((va, w, kind, reg))
    for k in sorted(hits):
        out.write('\n## K = %d (0x%X)  —— %s   [%d 处]\n' % (k, k, GEOM[k], len(hits[k])))
        for (va, w, kind, reg) in hits[k]:
            out.write('   %08x  %08x  %-52s  ; %s\n'
                      % (va, w, dis_r5900(w, va), reg_name(reg)))
    out.write('\n# ── 汇总表 ──\n')
    for k in sorted(hits):
        out.write('  K=%-6d (0x%-4X) 处数=%-4d  %s\n' % (k, k, len(hits[k]), GEOM[k]))
    return hits


GPRN = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]


def reg_name(i):
    return '$' + GPRN[i]


def diff(a, b, out):
    out.write('# A = %s\n# B = %s\n' % (a_path, b_path))
    out.write('# size A/B = %d / %d\n' % (len(a.d), len(b.d)))
    out.write('# segs A = %s\n# segs B = %s\n' % (a.segs, b.segs))
    n = min(len(a.d), len(b.d))
    # 逐字（4B）对齐比较，只报 ELF 文件偏移 4 字节对齐处
    runs = []
    cur = None
    for off in range(0, n - 3, 4):
        wa = struct.unpack_from('<I', a.d, off)[0]
        wb = struct.unpack_from('<I', b.d, off)[0]
        if wa != wb:
            if cur is None:
                cur = [off, []]
            cur[1].append((off, wa, wb))
        else:
            if cur is not None:
                runs.append(cur)
                cur = None
    if cur is not None:
        runs.append(cur)
    out.write('# 差异 run = %d ; 差异字 = %d ; 差异字节 = %d\n'
              % (len(runs), sum(len(r[1]) for r in runs),
                 sum(1 for o in range(n) if a.d[o] != b.d[o])))
    try:
        a2o = a.va2off
        b2o = b.va2off
    except Exception:
        a2o = b2o = None
    for (off0, items) in runs:
        # 用 A 的 VA 映射反推 VA
        va = None
        for (v, o, s, _fl) in a.segs:
            if o <= off0 < o + s:
                va = v + (off0 - o)
                break
        out.write('\n## run @ ELF off 0x%08X %s (%d 字)\n'
                  % (off0, ('VA 0x%08X' % va) if va is not None else '(不在段内)', len(items)))
        for (off, wa, wb) in items:
            vv = (va + (off - off0)) if va is not None else None
            out.write('   off %08X  VA %s\n' % (off, ('%08X' % vv) if vv else '--------'))
            out.write('      A %08x  %s\n' % (wa, dis_r5900(wa, vv or 0)))
            out.write('      B %08x  %s\n' % (wb, dis_r5900(wb, vv or 0)))
    return runs


def sites(elf, out):
    """把"参与格子/行/列/槽/UV/步进算术"的站点逐条列出（人工登记表 + 实读）。"""
    tbl = [
        (0x416ED0, 'decode cave 入口 (DrawString 的 jal 目标)'),
        (0x416ED8, 'decode: 默认步长 1'),
        (0x416EDC, 'decode: lead 下界 0xA1'),
        (0x416EE8, 'decode: GATE 前导上界 (A=0xB1 / B=0xBA)'),
        (0x416EF4, 'decode: len-1'),
        (0x416F08, 'decode: trail 读取'),
        (0x416F0C, 'decode: trail 下界 0xA1'),
        (0x416F18, 'decode: trail 上界 0xFF'),
        (0x416F24, 'decode: lead<<8'),
        (0x416F28, 'decode: |trail'),
        (0x416F30, 'decode: 步长 2'),
        (0x416F40, 'CharWidth cave 入口'),
        (0x416F90, 'CW: lead-0xA1'),
        (0x416F98, 'CW: trail-0xA1'),
        (0x416F9C, 'CW: PAIR_STRIDE 94'),
        (0x416FA0, 'CW: ★mult rd=t0,rs=t1,rt=t6 ⇒ t0=(lead-0xA1)*94'),
        (0x416FA4, 'CW: t0 += (trail-0xA1)'),
        (0x416FA8, 'CW: t0 += 0xE0 (单字节码位基数)'),
        (0x416FB0, 'CW: count = [FD+0x44]'),
        (0x416FBC, 'CW: 越界返回宽 16'),
        (0x416FC8, 'CW: 记录基址 [FD+0x38]'),
        (0x416FCC, 'CW: 记录索引 *10 (sll2/addu/sll1)'),
        (0x416FDC, 'CW: 记录 +1 = 字宽字节'),
        (0x417050, 'UV cave 入口 (GetGlyphUV)'),
        (0x417078, 'UV: lead 掩码'),
        (0x41707C, 'UV: lead-0xA1'),
        (0x417084, 'UV: trail-0xA1'),
        (0x417088, 'UV: PAIR_STRIDE 94'),
        (0x41708C, 'UV: ★mult rd=t4,rs=t4,rt=t6 ⇒ t4=(lead-0xA1)*94'),
        (0x417090, 'UV: t4 += (trail-0xA1)'),
        (0x417094, 'UV: idx = t4 + 0xE0'),
        (0x417098, 'UV: count'),
        (0x4170A8, 'UV: slot = idx - 0xE0'),
        (0x4170AC, 'UV: ★NCOL (A=62 / B=64)'),
        (0x4170B0, 'UV: div rd=zero ⇒ 商进 LO'),
        (0x4170B4, 'UV: mflo ⇒ row = slot / NCOL'),
        (0x4170B8, 'UV: row * NCOL'),
        (0x4170C0, 'UV: col = slot - row*NCOL'),
        (0x4170C4, 'UV: 16'),
        (0x4170C8, 'UV: U0 = 16*col'),
        (0x4170D0, 'UV: a1 = U0'),
        (0x4170D4, 'UV: U1 = U0 + 16'),
        (0x4170D8, 'UV: 阈值 12'),
        (0x4170DC, 'UV: row < 12 ?'),
        (0x4170E8, 'UV: ★SKIP_ROWS (A=3 / B=2)'),
        (0x4170EC, 'UV: 16'),
        (0x4170F0, 'UV: row * 16'),
        (0x4170F8, 'UV: ★V0 = row*16 + (A=2 / B=3)'),
        (0x4170FC, 'UV: ★V1 = row*16 + (A=18 / B=19)'),
        (0x417134, 'UV: 记录路径基址 [FD+0x38]'),
        (0x417138, 'UV: j 0x21AE20 (引擎记录读取)'),
        (0x417150, 'StringWidth cave 入口'),
        (0x417160, 'SW: GATE 前导上界'),
        (0x41717c, 'SW: trail 读取'),
        (0x4171ac, 'SW: i += 2 —— ★注意写的是 s4 (不是 s0!)'),
        (0x4171b0, 'SW: j 0x21AC84'),
        (0x4171c0, 'SW: j 0x21AC7C (单字节 i += 1)'),
        (0x41751C, 'gate #3'),
        (0x5656A4, 'gate #4'),
        (0x219BCC, 'DrawString: jal decode cave'),
        (0x219BD0, 'DrawString: a0 = sp+0xDE'),
        (0x219BD4, 'DrawString: lhu a1,[sp+0xDE]'),
        (0x219DAC, 'DrawString: lbu 步长 [sp+0xDD]'),
        (0x219DB0, 'DrawString: s0 += 步长'),
        (0x21A040, 'AddOneWord 主包复位闸门'),
        (0x21A144, 'AddOneWord 副包复位闸门'),
        (0x21AC6C, 'StringWidth: v0 = str + i'),
        (0x21AC70, 'StringWidth: lb a1,0(v0)'),
        (0x21AC74, 'StringWidth: j 0x417150'),
        (0x21AC78, 'StringWidth: 延迟槽'),
        (0x21AD10, 'CharWidth 入口 prologue'),
        (0x21AD18, 'CharWidth: j 0x416F40'),
        (0x21ADE0, 'GetGlyphUV: j 0x417050'),
    ]
    out.write('# %s\n# ── A.3/A.4 参与"格子/行/列/槽/UV/步进"的站点逐条实读 ──\n' % elf_path)
    out.write('%-12s %-10s %-62s %s\n' % ('VA', 'word', 'R5900', '登记语义'))
    for (va, note) in tbl:
        try:
            w = elf.word(va)
        except SystemExit:
            out.write('  %08X  <不可读>  %s\n' % (va, note))
            continue
        out.write('  %08X  %08X  %-62s %s\n' % (va, w, dis_r5900(w, va), note))
    return tbl


elf_path = ''
a_path = ''
b_path = ''


def main():
    global elf_path, a_path, b_path
    argv = sys.argv[:]
    outpath = None
    if '-o' in argv:
        i = argv.index('-o')
        outpath = argv[i + 1]
        del argv[i:i + 2]
    out = (open(outpath, 'w', encoding='utf-8', newline='\n') if outpath
           else sys.stdout)
    if not outpath:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode = argv[1]
    if mode == 'census':
        elf_path = argv[2]
        census(Elf(elf_path), out)
    elif mode == 'diff':
        a_path, b_path = argv[2], argv[3]
        elf_path = os.path.basename(a_path) + ' vs ' + os.path.basename(b_path)
        diff(Elf(a_path), Elf(b_path), out)
    elif mode == 'sites':
        elf_path = argv[2]
        sites(Elf(elf_path), out)
    else:
        raise SystemExit(__doc__)
    if outpath:
        out.close()
        print('[out] %s' % outpath)


if __name__ == '__main__':
    main()
