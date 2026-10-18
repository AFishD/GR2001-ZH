# -*- coding: utf-8 -*-
r"""nh_stage13_ctx.py — 关键 ELF 差异点的上下文反汇编 (只读)"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nh_lib as N   # noqa: E402
import nh_elf as E   # noqa: E402
import nh_stage3_elf as S3   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SITES = [
    ('run#15 AddOneWord +0xA4', 0x219FF4),
    ('run#16 AddOneWord +0x1A8', 0x21A0F8),
    ('run#17 Flush      +0x34', 0x21A1C4),
    ('run#18 Draw       +0x34', 0x21A2C4),
    ('run#2  DrawLetters+0xB8', 0x216578),
    ('run#14 DrawString +0x33C', 0x219DAC),
    ('run#5  DrawString +0x15C', 0x219BCC),
    ('run#22 CompCharTC +0x0', 0x21ADE0),
    ('fix     s_Pool    +0x1FF0', 0x5657E0),
]


def main():
    e_en, _ = S3.load_elf('EN_ORIG')
    e_zh, _ = S3.load_elf('ZH113b_fix')
    buf = io.StringIO()
    for (lbl, center) in SITES:
        sym = e_en.sym_at(center)
        buf.write('=' * 96 + '\n%s  VA 0x%X  in %s +0x%X\n'
                  % (lbl, center, sym['name'] if sym else '?',
                     center - sym['value'] if sym else 0))
        for k in range(-10, 12):
            va = center + k * 4
            o, _ = e_en.va2off(va)
            if o is None:
                continue
            we = struct.unpack_from('<I', e_en.b, o)[0]
            wz = struct.unpack_from('<I', e_zh.b, o)[0]
            mark = '  ' if we == wz else ' *'
            buf.write('%s 0x%08X  EN %08X %-32s | ZH %08X %-32s\n'
                      % (mark, va, we, E.mips_dis1(we, va), wz, E.mips_dis1(wz, va)))
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage13_ctx.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
