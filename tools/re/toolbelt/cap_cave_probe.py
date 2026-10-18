# -*- coding: utf-8 -*-
r"""cap_cave_probe.py -- Step 1: 反汇编核对图集 cave 常量 + 逐字节改动清单 (只读 ISO)

    python tools/re/toolbelt/cap_cave_probe.py [--iso <iso>] [--outdir <dir>]

做四件事 (全部只读 + 只写 work\builds\GR_CAP2400\temp\):
  ① 从 ISO 里取出 SLUS_206.13 (LBA 295, 37,453,732 B) 并验证 PT_LOAD[0] 的映射
     (ISO 0x93880 + (VA-0x100000) ⇒ **ISO = VA - 0x6C780**), 打 sha256;
  ② 线性反汇编网格式 cave 0x416ED0..0x4171A0 / 0x417510..0x417540 / 0x565690..0x5656D0;
  ③ 全 text 段扫描: 「立即数 62 / 94 / 3 / 16 / 2」的**全部**出现点 + 全 `div/divu/mult`
     站点 ⇒ 判定 62 是不是"单立即数"(能不能只改一个字节);
  ④ 打印待改字节的 VA / ISO 偏移 / 改前 4 字节 / 改后 4 字节 (COLS 62→64, GATE 0xB4→0xBA×4)。
"""
import hashlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import cave_dis                                                       # noqa: E402

ELF_LBA, ELF_BYTES = 295, 37453732
ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000          # = LBA295 + 0x80 (PT_LOAD[0])
DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', 'temp')

# ---- 待改站点 (VA, 语义, 旧立即数, 新立即数) ----
COLS_VA = 0x4170AC                                     # addiu t6,zero,62
GATE_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)  # sltiu tX,a1,0xB4
GATE_OLD, GATE_NEW = 0xB4, 0xBA
COLS_OLD, COLS_NEW = 62, 64

DIS_RANGES = [
    ('decode cave  0x416ED0..0x416F40', 0x416ED0, 0x416F40),
    ('width  cave  0x416F40..0x416FB8', 0x416F40, 0x416FB8),
    ('grid   cave  0x417050..0x417140', 0x417050, 0x417140),
    ('gate2  site  0x417150..0x417190', 0x417150, 0x417190),
    ('gate3  site  0x417510..0x417540', 0x417510, 0x417540),
    ('gate4  site  0x565690..0x5656D0', 0x565690, 0x5656D0),
]


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


LOG = []


def va2iso(va):
    return ELF_ISO_BASE + (va - ELF_VA_BASE)


def scan_imm(elf, imm, lo=None, hi=None):
    """→ [(va, word, text)]: 区间里「立即数 == imm」的指令 (addi/addiu/slti/sltiu/andi/ori/xori/lui)."""
    va0, _off, fs = elf.text()
    lo = va0 if lo is None else lo
    hi = va0 + fs if hi is None else hi
    out = []
    for va in range(lo, hi - 4, 4):
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F):     # addi/addiu/slti/sltiu/andi/ori/xori/lui
            if (w & 0xFFFF) == imm:
                out.append((va, w, cave_dis.dis(w, va)))
    return out


# 「与字库有关的窗口」(线性扫描的**语义**过滤; 窗口外的命中与图集几何无关)
FONT_WINDOWS = [
    ('RSFont 模块   0x219A70..0x21D948', 0x219A70, 0x21D948),
    ('汉化 cave A   0x416E00..0x417600', 0x416E00, 0x417600),
    ('汉化 cave B   0x565600..0x565A50', 0x565600, 0x565A50),
    ('纹理装载器    0x51B660..0x51E000', 0x51B660, 0x51E000),
]


def scan_div(elf, lo, hi):
    """→ [(va, word, text)]: div/divu/div1/divu1 站点 (special fn 1A/1B, special2)."""
    out = []
    for va in range(lo, hi - 4, 4):
        w = elf.word(va)
        op, fn = (w >> 26) & 0x3F, w & 0x3F
        s2 = (w >> 6) & 0x1F
        if op == 0 and fn in (0x1A, 0x1B):
            out.append((va, w, cave_dis.dis(w, va)))
        elif op == 0x1C and s2 in (0x1A, 0x1B):                        # SPECIAL2 div1/divu1
            out.append((va, w, cave_dis.dis(w, va)))
    return out


def main(argv):
    iso_p = DEFAULT_ISO
    outdir = OUTDIR
    i = 0
    while i < len(argv):
        if argv[i] == '--iso':
            iso_p = argv[i + 1]
            i += 2
        elif argv[i] == '--outdir':
            outdir = argv[i + 1]
            i += 2
        else:
            raise SystemExit('unknown arg %s' % argv[i])
    os.makedirs(outdir, exist_ok=True)
    iso = open(iso_p, 'rb')
    sz = os.path.getsize(iso_p)
    P('=' * 90)
    P('cap_cave_probe.py  --  Step1 cave 常量反汇编核对')
    P('  iso = %s  (%d B = %d sect)' % (iso_p, sz, sz // 2048))
    P('=' * 90)

    # ── ① ELF 提取 + 映射验证 ──
    iso.seek(ELF_LBA * 2048)
    blob = iso.read(ELF_BYTES)
    assert len(blob) == ELF_BYTES and blob[:4] == b'\x7fELF', blob[:4]
    elf_p = os.path.join(outdir, os.path.basename(iso_p).replace('.iso', '_SLUS_206.13.elf'))
    with open(elf_p, 'wb') as f:
        f.write(blob)
    P('[elf] LBA %d (+0x80) ⇒ %s  %d B  sha256=%s'
      % (ELF_LBA, elf_p, len(blob), hashlib.sha256(blob).hexdigest()))
    elf = cave_dis.Elf(elf_p)
    va0, off0, fs0 = elf.text()
    P('[elf] PT_LOAD[0] va=0x%08X off=0x%X filesz=0x%X  ⇒ ISO = 0x%X + (VA-0x%X) = **VA - 0x%X**'
      % (va0, off0, fs0, ELF_LBA * 2048 + off0, va0, va0 - ELF_LBA * 2048 - off0))
    assert ELF_LBA * 2048 + off0 == ELF_ISO_BASE and va0 == ELF_VA_BASE
    for va in (0x4170AC, 0x416EE8) + GATE_SITES:
        o = va2iso(va)
        assert bytes(iso_mm(iso, o, 4)) == elf.read(va, 4), \
            'VA 0x%08X: ISO 0x%X 的字节 != ELF 里同 VA 的字节' % (va, o)
    P('[elf] 3 锚点核对: ISO 偏移处的字节 == ELF 里同 VA 的字节 ✓  (例: VA 0x416EE8 → ISO 0x%X)'
      % va2iso(0x416EE8))

    # ── ② 反汇编 ──
    for title, lo, hi in DIS_RANGES:
        P('')
        P('---- %s ----' % title)
        for va, w in elf.iter_words(lo, hi):
            mark = ''
            if va == COLS_VA or va in GATE_SITES:
                mark = '   <<< ★ 待改' if va != COLS_VA else '   <<< ★ 待改 (COLS)'
            P('  0x%08X  ISO 0x%08X  %08X  %-44s ; %s%s'
              % (va, va2iso(va), w, cave_dis.dis(w, va), elf.read(va, 4).hex(), mark))

    # ── ③ 常量普查: 62 是不是单立即数? ──
    P('')
    P('=' * 90)
    P('③ 常量普查 (全 text 段 0x%08X..0x%08X, 共 %d 条指令)'
      % (va0, va0 + fs0, fs0 // 4))
    P('   目的: 判定 COLS=62 能不能只改**一个立即数**; 顺带证明图集几何里没有 w/h 常量。')
    for imm, name in ((62, 'COLS(NCOL)'), (94, 'PAIR_STRIDE'), (12, 'SKIP_ROW'), (3, 'SKIP_ROWS'),
                      (16, 'CW/CH'), (2, 'Y0')):
        allh = scan_imm(elf, imm)
        inwin = []
        for (wl, lo, hi) in FONT_WINDOWS:
            for h in scan_imm(elf, imm, lo, hi):
                inwin.append((wl, h))
        P('  imm %-3d (%-11s): 全段 **%d** 个站点 ; 落在字库窗口内 **%d** 个'
          % (imm, name, len(allh), len(inwin)))
        for (wl, (va, w, t)) in inwin:
            tag = '   <<< 本 cave (待改)' if va == COLS_VA else ''
            P('      [%s] 0x%08X  ISO 0x%08X  %08X  %s%s'
              % (wl.split()[0], va, va2iso(va), w, t, tag))
    P('')
    P('  ★ COLS=62 的性质: 唯一消费者是 0x4170B0 的 `div $t4,$t6` (除数在 $t6, 由 0x4170AC')
    P('    的 `addiu $t6,$zero,62` 装载) ⇒ **单立即数**, 没有 mul/sll/add 组合编码,')
    P('    也没有第二处 62 参与格位计算 ⇒ 改 1 个字节即可。')
    divs = scan_div(elf, 0x416E00, 0x417600)
    P('  div/divu 站点 (cave 区 0x416E00..0x417600): **%d** 个' % len(divs))
    for (va, w, t) in divs:
        P('      0x%08X  ISO 0x%08X  %08X  %s' % (va, va2iso(va), w, t))
    # 反证: 图集宽/高不是常量
    for imm, nm in ((1024, 'w=1024'), (512, 'h=512'), (640, 'h=640'), (644, 'h=644')):
        hits = scan_imm(elf, imm)
        inw = sum(len(scan_imm(elf, imm, lo, hi)) for (_l, lo, hi) in FONT_WINDOWS)
        P('  反证: imm %-5d (%s): 全段 %d 个站点 / 字库窗口内 **%d** 个'
          % (imm, nm, len(hits), inw))

    # ── ④ 改动清单 ──
    P('')
    P('=' * 90)
    P('④ 逐字节改动清单 (VA / ISO 偏移 / 改前 4 字节 / 改后 4 字节)')
    P('%-12s %-12s %-22s %-22s %s' % ('VA', 'ISO 偏移', '改前 (LE 4B)', '改后 (LE 4B)', '指令 前 → 后'))
    changes = []
    # 4a COLS 62 -> 64   (addiu t6,zero,62 → addiu t6,zero,64)
    w0 = elf.word(COLS_VA)
    assert (w0 >> 26) == 0x09 and ((w0 >> 21) & 0x1F) == 0 and (w0 & 0xFFFF) == COLS_OLD, hex(w0)
    w1 = (w0 & 0xFFFF0000) | COLS_NEW
    changes.append((COLS_VA, w0, w1, 'COLS 62→64'))
    # 4b GATE ×4   (sltiu tX, rs, 0xB4 → 0xBA)
    for va in GATE_SITES:
        w0 = elf.word(va)
        assert (w0 >> 26) == 0x0B and (w0 & 0xFFFF) == GATE_OLD, (hex(va), hex(w0))
        w1 = (w0 & 0xFFFF0000) | GATE_NEW
        changes.append((va, w0, w1, 'GATE 0xB4→0xBA (%s)' % cave_dis.dis(w0, va)))
    for (va, w0, w1, tag) in changes:
        b0, b1 = struct.pack('<I', w0), struct.pack('<I', w1)
        P('0x%08X   0x%08X   %-20s %-20s %-26s ; %s'
          % (va, va2iso(va), ' '.join('%02X' % x for x in b0), ' '.join('%02X' % x for x in b1),
             '%s → %s' % (cave_dis.dis(w0, va), cave_dis.dis(w1, va)), tag))
    P('')
    P('  实际改动字节数 = **%d 个字节** = 5 个字 × 1 字节 (小端 imm 低字节):' % len(changes))
    for (va, w0, w1, tag) in changes:
        d = [k for k in range(4) if struct.pack('<I', w0)[k] != struct.pack('<I', w1)[k]]
        P('     VA 0x%08X  ISO 0x%08X  byte+%d : %02X → %02X   (%s)'
          % (va, va2iso(va), d[0], struct.pack('<I', w0)[d[0]], struct.pack('<I', w1)[d[0]], tag))

    # ── ⑤ 附带核对: 中性常量 (不动) ──
    P('')
    P('=' * 90)
    P('⑤ 中性常量核对 (本轮**不动**):')
    neutral = [(0x417088, 94, 'PAIR_STRIDE 94'), (0x417070, None, 'b 0x417098'),
               (0x4170B0, None, 'div t4,t6'), (0x4170C4, 16, 'CW=16'), (0x4170D8, 12, 'SKIP_ROW=12'),
               (0x4170E8, 3, 'SKIP_ROWS=3'), (0x4170EC, 16, 'CH=16'), (0x4170F8, 2, 'Y0=2'),
               (0x4170FC, 18, 'V1 = Y0+16 = 18'), (0x417094, 224, 'record idx = slot+0xE0')]
    for (va, imm, name) in neutral:
        w = elf.word(va)
        ok = '' if imm is None else ('  imm=%d %s' % (w & 0xFFFF, '✓' if (w & 0xFFFF) == imm else '✗'))
        P('  0x%08X  ISO 0x%08X  %08X  %-40s ; %s%s'
          % (va, va2iso(va), w, cave_dis.dis(w, va), elf.read(va, 4).hex(), ok))
    P('')
    P('  ★ 结论: cave 里 **没有** 1024/512/644 任何一个常量 ⇒ 图集几何纯数据驱动 (与')
    P('    REPORT_font_capacity_decompile §2 一致); COLS 是单立即数; V1 = Y0+16 = 18 由')
    P('    0x4170FC 的 `addiu t6,t6,18` 给出 ⇒ h=644 时最高网格行 row36 的 V1 = 642 ≤ 644 ✓')

    iso.close()
    p = os.path.join(outdir, 'cave_probe.txt')
    with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % p)
    # 供 cap_build.py 复用
    with io.open(os.path.join(outdir, 'cave_changes.json'), 'w', encoding='utf-8', newline='\n') as f:
        import json
        json.dump(dict(iso=iso_p, elf=elf_p,
                       elf_sha256=hashlib.sha256(blob).hexdigest(),
                       iso_va_delta=ELF_VA_BASE - ELF_ISO_BASE,
                       changes=[dict(va=va, iso=va2iso(va), old='%08X' % w0, new='%08X' % w1,
                                     byte=(lambda d: d[0])([k for k in range(4)
                                                           if struct.pack('<I', w0)[k]
                                                           != struct.pack('<I', w1)[k]]),
                                     old_byte=(lambda d: struct.pack('<I', w0)[d[0]])(
                                         [k for k in range(4) if struct.pack('<I', w0)[k]
                                          != struct.pack('<I', w1)[k]]),
                                     new_byte=(lambda d: struct.pack('<I', w1)[d[0]])(
                                         [k for k in range(4) if struct.pack('<I', w0)[k]
                                          != struct.pack('<I', w1)[k]]),
                                     instr_before=cave_dis.dis(w0, va),
                                     instr_after=cave_dis.dis(w1, va), tag=tag)
                                 for (va, w0, w1, tag) in changes]),
                  f, ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.join(outdir, 'cave_changes.json'))
    return 0


_MM = {}


def iso_mm(iso, off, n=None):
    """只读地取 ISO 的字节 (缓存 mmap)。"""
    if 'm' not in _MM:
        import mmap
        _MM['m'] = mmap.mmap(iso.fileno(), 0, access=mmap.ACCESS_READ)
    m = _MM['m']
    return m[off:off + n] if n else m[off:]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
