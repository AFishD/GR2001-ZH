# -*- coding: utf-8 -*-
r"""nh_stage4_elfdis.py — 对每个 ELF 差异 run 做指令级对照 (只读)

输出 evidence/stage4_elf_disasm.txt
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402
import nh_stage3_elf as S3   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    e_en, _ = S3.load_elf('EN_ORIG')
    e_zh, _ = S3.load_elf('ZH113b_fix')
    e_zh0, _ = S3.load_elf('ZH113b')
    raw, merged = S3.exact_runs(e_en.b, e_zh.b)

    buf = io.StringIO()
    buf.write('ELF 差异 run 的指令级对照 (EN_ORIG vs ZH113b_fix)\n')
    buf.write('ELF: main 段 VA 0x100000..0x5DED00 <-> FILE 0x80..0x4DED80 ; 映射 off = VA - 0xFFF80\n')
    buf.write('总计 %d 个精确 run / %s B; 合并 %d 处\n\n'
              % (len(raw), N.fmt(sum(e - s for s, e in raw)), len(merged)))
    for i, (s, e) in enumerate(merged):
        va, _ = e_en.off2va(s)
        sym = e_en.sym_at(va) if va else None
        # 对齐到 4 字节
        a0 = s & ~3
        a1 = (e + 3) & ~3
        buf.write('=' * 96 + '\n')
        buf.write('run#%d  FILE 0x%X..0x%X  len=%-4d  VA 0x%X..0x%X  %s +0x%X  (sym size=%s)\n'
                  % (i, s, e, e - s, va, (e_en.off2va(e - 1)[0] or 0),
                     sym['name'] if sym else '?',
                     (va - sym['value']) if sym else 0,
                     sym['size'] if sym else '?'))
        for o in range(a0, a1, 4):
            ova, _ = e_en.off2va(o)
            we = struct.unpack_from('<I', e_en.b, o)[0]
            wz = struct.unpack_from('<I', e_zh.b, o)[0]
            mark = '  ' if we == wz else ' *'
            buf.write('%s 0x%08X  EN %08X %-34s | ZH %08X %-34s\n'
                      % (mark, ova, we, E.mips_dis1(we, ova), wz, E.mips_dis1(wz, ova)))
        # 若该 run 不是 4 对齐指令边界, 打印原始字节
        if (e - s) % 4 or (s % 4):
            buf.write('     原始字节 EN %s\n' % e_en.b[s:e].hex(' '))
            buf.write('     原始字节 ZH %s\n' % e_zh.b[s:e].hex(' '))

    # ---------------- ZH113b -> ZH113b_fix 的 "+1 字节修复" ----------------
    r2, m2 = S3.exact_runs(e_zh0.b, e_zh.b)
    buf.write('\n\n' + '=' * 96 + '\n')
    buf.write('ZH113b -> ZH113b_fix 的 ELF 差异 (任务书称 "+1 字节修复版")\n')
    buf.write('  精确差异 run = %d, 字节 = %s\n' % (len(r2), N.fmt(sum(e - s for s, e in r2))))
    for (s, e) in r2:
        va, _ = e_zh0.off2va(s)
        sym = e_zh0.sym_at(va) if va else None
        buf.write('  FILE 0x%06X..0x%06X len=%-3d VA 0x%X  %s +0x%X\n'
                  % (s, e, e - s, va, sym['name'] if sym else '?',
                     (va - sym['value']) if sym else 0))
        for o in range(s & ~3, (e + 3) & ~3, 4):
            ova, _ = e_zh0.off2va(o)
            w0 = struct.unpack_from('<I', e_zh0.b, o)[0]
            w1 = struct.unpack_from('<I', e_zh.b, o)[0]
            mark = '  ' if w0 == w1 else ' *'
            buf.write('%s 0x%08X  b   %08X %-34s | fix %08X %-34s\n'
                      % (mark, ova, w0, E.mips_dis1(w0, ova), w1, E.mips_dis1(w1, ova)))

    with open(os.path.join(N.EVID, 'stage4_elf_disasm.txt'), 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())
    print(buf.getvalue())


if __name__ == '__main__':
    main()
