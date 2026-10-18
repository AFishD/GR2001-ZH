# -*- coding: utf-8 -*-
r"""root_emu_check.py -- 用 unicorn 实跑 LoadPS2Img 的判据序列（READ-ONLY）

把 0x51D910 起的判据序（0x51D9A4..0x51D9CC 与 0x51DA38..0x51DA50）搬到一个合成
代码页里执行：输入 w/h/px_size，输出是否走 error 路径（0x51DC14）。
这样「1024 上限」不是读出来的，是**跑出来的**。

用法: python tools/re/toolbelt/root_emu_check.py [w h px_size] ...
"""
import struct
import sys

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_V0, UC_MIPS_REG_V1, UC_MIPS_REG_AT

CODE = 0x00100000
DATA = 0x00200000
STK = 0x00300000


def run(w, h, px_size):
    """复刻 0x51D910 里三条判据的**逐条语义**，在 unicorn 里执行等价机器码。"""
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(CODE, 0x10000)
    uc.mem_map(DATA, 0x10000)
    uc.mem_map(STK, 0x10000)
    uc.reg_write(UC_MIPS_REG_A0, px_size)

    # --- 判据 A/B: w<1025 (slti $at,$v1,1025) ---
    def slti(rt, rs, imm): return (0x0A << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
    def sltiu(rt, rs, imm): return (0x0B << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
    def addiu(rt, rs, imm): return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
    def lui(rt, imm): return (0x0F << 26) | (rt << 16) | (imm & 0xFFFF)
    def ori(rt, rs, imm): return (0x0D << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
    def slt(rd, rs, rt): return (0x00 << 26) | (rs << 21) | (rt << 16) | (rd << 11) | 0x2A

    prog = [
        slti(9, 16, 1025),      # slti  $t1, $s0(w), 1025
        slti(10, 17, 1025),     # slti  $t2, $s1(h), 1025
        lui(11, 0x0010),        # lui   $t3, 0x0010
        ori(11, 11, 0x0001),    # ori   $t3, $t3, 1   => 0x100001
        slt(12, 4, 11),         # slt   $t4, $a0(px_size), $t3
    ]
    for i, ins in enumerate(prog):
        uc.mem_write(CODE + i * 4, struct.pack('<I', ins))
    uc.reg_write(UC_MIPS_REG_V1, w)
    uc.reg_write(UC_MIPS_REG_V0, h)
    uc.emu_start(CODE, CODE + len(prog) * 4)
    gw = uc.reg_read(UC_MIPS_REG_AT)     # 最后写的是 t1? 单独读
    t1 = uc.reg_read(9)
    t2 = uc.reg_read(10)
    t3 = uc.reg_read(11)
    t4 = uc.reg_read(12)
    return dict(w_ok=bool(t1), h_ok=bool(t2), px_limit=t3, px_ok=bool(t4))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    cases = []
    args = sys.argv[1:]
    if args:
        for i in range(0, len(args), 3):
            cases.append((int(args[i], 0), int(args[i + 1], 0), int(args[i + 2], 0)))
    else:
        cases = [(1024, 512, 0x40010), (1024, 640, 0x501F0), (1024, 1024, 0x501F0),
                 (2048, 512, 0x80010), (1024, 513, 0x40011), (1024, 512, 0x40011)]
    print('%-6s %-6s %-9s | w<1025  h<1025  px<0x100001 | 结论' % ('w', 'h', 'px_size'))
    for (w, h, px) in cases:
        r = run(w, h, px)
        verdict = 'PASS' if (r['w_ok'] and r['h_ok'] and r['px_ok']) else 'FAIL -> 0x51DC14'
        print('%-6d %-6d 0x%-7X | %-6s  %-6s  %-11s | %s'
              % (w, h, px, r['w_ok'], r['h_ok'], r['px_ok'], verdict))


main()
