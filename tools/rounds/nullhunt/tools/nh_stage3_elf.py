# -*- coding: utf-8 -*-
r"""nh_stage3_elf.py — ELF(SLUS_206.13) 逐字节差异 + 停顿 PC 归属  (只读)

输出:
  evidence/stage3_elf_layout.txt   ELF 头/段表/节表/符号抽样
  evidence/stage3_stall_pc.txt     停顿 PC 的 VA->文件偏移->符号->反汇编, 并核对 EN/ZH 是否同字节
  evidence/stage3_elf_diff.txt     EN vs ZH 的 ELF 精确差异 run, 并按符号归类
  evidence/stage3_elf_diff.json    机器可读
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(N.EVID, exist_ok=True)

STALL_PCS = [0x101d10, 0x101dd8, 0x101de4, 0x101e08, 0x101e34, 0x101e6c,
             0x101fe0, 0x102000, 0x102008, 0x102220, 0x1024d0, 0x102584,
             0x1024e8, 0x51b660, 0x51b7ac, 0x51b0d8, 0x51c4c0, 0x3f6038]


def load_elf(tag):
    iso = N.Iso(N.ISO[tag])
    f = [v for k, v in iso.files().items() if 'SLUS_206.13' in k][0]
    blob = iso.rd(f['lba'] * N.SEC, f['size'])
    iso.close()
    return E.Elf(blob, tag), f


def exact_runs(a, b):
    """逐字节精确差异 run (无 4K 对齐填充)。"""
    n = len(a)
    runs = []
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        while j < n and a[j] != b[j]:
            j += 1
        runs.append((i, j))
        i = j
    # 合并相邻 (被相同字节 1..3 分隔的 run 也合并, 便于阅读)
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 4:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return runs, merged


def main():
    e_en, f_en = load_elf('EN_ORIG')
    e_zh, f_zh = load_elf('ZH113b_fix')
    e_zh0, f_zh0 = load_elf('ZH113b')

    lay = io.StringIO()
    for tag, e, f in (('EN_ORIG', e_en, f_en), ('ZH113b_fix', e_zh, f_zh)):
        lay.write('=' * 100 + '\n%s  %s\n' % (tag, f))
        lay.write('  file size = %s B\n' % N.fmt(len(e.b)))
        lay.write('  e_type=%d machine=%d entry=0x%X phoff=0x%X phnum=%d shoff=0x%X shnum=%d shstrndx=%d\n'
                  % (e.type, e.machine, e.entry, e.phoff, e.phnum, e.shoff, e.shnum,
                     e.shstrndx))
        lay.write('  Program headers:\n%s\n' % e.report_phdrs())
        lay.write('  Section headers:\n%s\n' % e.report_shdrs())
        # VA->off 线性关系自证
        lay.write('  [自证] VA 0x101DD8 -> FILE 0x%X\n' % e.va2off(0x101DD8)[0])
        lay.write('  [自证] FILE 0x1E58 -> VA 0x%X\n' % e.off2va(0x1E58)[0])
        funcs = [s for s in e.syms if s['type'] == 2 and s['size']]
        lay.write('  符号: 共 %d 个, 其中 FUNC 带 size %d 个\n' % (len(e.syms), len(funcs)))
        lay.write('  地址最低的 12 个 FUNC 符号:\n')
        for s in sorted(funcs, key=lambda x: x['value'])[:12]:
            lay.write('    0x%08X size=%-6d %s\n' % (s['value'], s['size'], s['name']))
        lay.write('  === ELF 与 ISO 字节偏移关系: ELF 起于 LBA %d = 字节 0x%X ===\n'
                  % (f['lba'], f['lba'] * N.SEC))

    # ---------------- 停顿 PC ----------------
    pc = io.StringIO()
    pc.write('停顿 PC 归属 (ELF = SLUS_206.13, EN_ORIG 版)\n')
    pc.write('VA->FILE 映射: %s\n\n'
             % ' ; '.join('PH off=0x%X vaddr=0x%X filesz=0x%X'
                          % (p['off'], p['vaddr'], p['filesz'])
                          for p in e_en.phdrs if p['type'] == 1))
    pc.write('%-10s %-10s %-34s %-8s %s\n'
             % ('VA', 'FILE', 'SYMBOL', 'SYM+', 'EN/ZH 该地址 16 字节是否相同'))
    for va in STALL_PCS:
        off, ph = e_en.va2off(va)
        s = e_en.sym_at(va) if off is not None else None
        same = 'n/a'
        if off is not None:
            same = ('SAME' if e_zh.b[off:off + 16] == e_en.b[off:off + 16]
                    else 'DIFF!')
        pc.write('0x%08X 0x%-8s %-34s +0x%-5s %s\n'
                 % (va, ('%X' % off) if off is not None else '??',
                    (s['name'] if s else '??'),
                    ('%X' % (va - s['value'])) if s else '?', same))
    pc.write('\n---- 停顿点邻域反汇编 (EN_ORIG) ----\n')
    for center in (0x1024d0, 0x102584, 0x101dd8, 0x101e34, 0x102008):
        off, _ = e_en.va2off(center)
        if off is None:
            pc.write('VA 0x%X 不在任何 PT_LOAD 内\n' % center)
            continue
        s = e_en.sym_at(center)
        pc.write('\n### VA 0x%X  (FILE 0x%X)  in %s +0x%X\n'
                 % (center, off, s['name'] if s else '?', center - s['value'] if s else 0))
        base = center - 0x20
        for k in range(-8, 12):
            va = base + k * 4
            o, _ = e_en.va2off(va)
            if o is None:
                continue
            w_en = struct.unpack_from('<I', e_en.b, o)[0]
            w_zh = struct.unpack_from('<I', e_zh.b, o)[0]
            mark = '   ' if w_en == w_zh else ' * '
            pc.write('  %s0x%08X  0x%08X  %-34s %s\n'
                     % (mark, va, w_en, E.mips_dis1(w_en, va),
                        '' if w_en == w_zh else 'ZH=0x%08X %s'
                        % (w_zh, E.mips_dis1(w_zh, va))))
    pc.write('\n(* = 汉化改过这条指令)\n')

    # ---------------- ELF 精确差异 ----------------
    assert len(e_en.b) == len(e_zh.b), 'ELF 尺寸不同'
    raw_runs, merged = exact_runs(e_en.b, e_zh.b)
    db = io.StringIO()
    db.write('ELF 精确差异: EN_ORIG vs ZH113b_fix\n')
    db.write('  ELF 尺寸 %s B (两者相同)\n' % N.fmt(len(e_en.b)))
    db.write('  精确差异 run = %d 个, 差异字节 = %s\n'
             % (len(raw_runs), N.fmt(sum(e - s for s, e in raw_runs))))
    db.write('  合并后 run (间距<=4B 合并) = %d 个, 覆盖 = %s B\n'
             % (len(merged), N.fmt(sum(e - s for s, e in merged))))
    db.write('\n%-4s %-10s %-10s %-8s %-8s %-9s %-28s %s\n'
             % ('#', 'FILE_OFF', 'VA', 'LEN', 'ZH_VA', 'DELTA_VA', 'SYMBOL', 'ZH_SYMBOL'))
    recs = []
    for i, (s, e) in enumerate(merged):
        va_s, _ = e_en.off2va(s)
        va_e, _ = e_en.off2va(e - 1)
        sym = e_en.sym_at(va_s) if va_s else None
        symz = e_zh.sym_at(va_s) if va_s else None
        rec = dict(idx=i, foff=s, foff_end=e, va=va_s, va_end=va_e, length=e - s,
                   sym=sym['name'] if sym else None,
                   sym_delta=(va_s - sym['value']) if sym else None,
                   sym_size=sym['size'] if sym else None,
                   zh_sym=symz['name'] if symz else None)
        # 是否落在某个节里
        sec = None
        for sh in e_en.shdrs:
            if sh['off'] <= s < sh['off'] + sh['size']:
                sec = sh['name']
                break
        rec['section'] = sec
        recs.append(rec)
        db.write('%-4d 0x%08X 0x%08X %-8d 0x%-6s +0x%-5s %-28s %s [%s]\n'
                 % (i, s, va_s, e - s, ('%X' % va_s) if va_s else '?',
                    ('%X' % (va_s - sym['value'])) if sym else '?',
                    (sym['name'] if sym else '?'), (symz['name'] if symz else '?'), sec))
    # 按符号归并统计
    agg = {}
    for r in recs:
        k = r['sym'] or '<no symbol>'
        a = agg.setdefault(k, [0, 0, None, None])
        a[0] += 1
        a[1] += r['length']
        a[2] = r['va'] if a[2] is None else min(a[2], r['va'])
        a[3] = r['foff'] if a[3] is None else min(a[3], r['foff'])
    db.write('\n按所属函数归并:\n')
    for k in sorted(agg, key=lambda k: -agg[k][1]):
        a = agg[k]
        db.write('  %-40s runs=%-3d bytes=%-8d min_VA=0x%X\n' % (k, a[0], a[1], a[2]))
    # 每个 run 的字节对照
    db.write('\n逐 run 字节对照 (ZH 与 EN 不同处, 每 run 最多 128 B):\n')
    for r in recs:
        s, e = r['foff'], r['foff_end']
        db.write('--- run#%d FILE 0x%X..0x%X len=%d VA 0x%X [%s +0x%X]\n'
                 % (r['idx'], s, e, r['length'], r['va'], r['sym'],
                    r['sym_delta'] if r['sym_delta'] is not None else -1))
        for k in range(0, min(e - s, 128), 16):
            x = e_en.b[s + k:s + k + 16]
            y = e_zh.b[s + k:s + k + 16]
            if x == y:
                continue
            db.write('    +0x%03X EN %s  |  ZH %s\n' % (k, x.hex(' '), y.hex(' ')))

    # --------- ZH113b vs ZH113b_fix (所谓 "+1 字节修复") ---------
    assert len(e_zh0.b) == len(e_zh.b)
    r2, m2 = exact_runs(e_zh0.b, e_zh.b)
    db.write('\n\n==== ZH113b vs ZH113b_fix (ELF) ====\n')
    db.write('  精确差异 run = %d, 字节 = %s\n' % (len(r2), N.fmt(sum(e - s for s, e in r2))))
    for (s, e) in r2:
        va, _ = e_zh0.off2va(s)
        sym = e_zh0.sym_at(va) if va else None
        db.write('  FILE 0x%08X..0x%08X len=%-6d VA 0x%X %s +0x%X\n'
                 % (s, e, e - s, va, sym['name'] if sym else '?',
                    (va - sym['value']) if sym else 0))
        for k in range(0, e - s, 16):
            db.write('    +0x%03X old %s | new %s\n'
                     % (k, e_zh0.b[s + k:s + k + 16].hex(' '),
                        e_zh.b[s + k:s + k + 16].hex(' ')))

    for fn, txt in (('stage3_elf_layout.txt', lay.getvalue()),
                    ('stage3_stall_pc.txt', pc.getvalue()),
                    ('stage3_elf_diff.txt', db.getvalue())):
        with open(os.path.join(N.EVID, fn), 'w', encoding='utf-8') as fh:
            fh.write(txt)
    with open(os.path.join(N.EVID, 'stage3_elf_diff.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(runs_raw=raw_runs, runs_merged=recs,
                       zh_vs_zhfix=r2, total_bytes=sum(e - s for s, e in raw_runs)), fh, indent=1)
    print(lay.getvalue())
    print(pc.getvalue())
    print(db.getvalue()[:26000])


if __name__ == '__main__':
    main()
