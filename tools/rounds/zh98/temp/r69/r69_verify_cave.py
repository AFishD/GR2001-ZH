# -*- coding: utf-8 -*-
r"""r69_verify_cave.py — 独立复核 patch_zh115_sfnowrap.py 的 MIPS 编码与语义。

不引用补丁模块的"意图", 直接把补丁写下的词按 MIPS 语义反解:
  · j 的目标地址对不对 (含延迟槽归属)
  · bne 的相对偏移对不对 (目标 = 出口 j)
  · 两条路径上 $s7 的最终值 (命中 ⇒ 0x7FFF0000; 未命中 ⇒ comp[0x40]-comp[0xB4])
"""
import struct
import sys

HOOK_VA = 0x21CC90
CAVE_VA = 0x5659A8
CAVE = [0x0062B823, 0x3C080059, 0x250878C0, 0x8EA10000, 0x14280007, 0x2401010E,
        0x14610005, 0x8EA20044, 0x240100BE, 0x14410002, 0x00000000, 0x3C177FFF,
        0x08087325, 0x00000000]
NEW_HOOK = 0x0815966A


def s16(x):
    return x - 0x10000 if x >= 0x8000 else x


def main():
    ok = True

    def chk(cond, msg):
        nonlocal ok
        print('  %s %s' % ('✓' if cond else '✗', msg))
        if not cond:
            ok = False

    print('== 1. 挂点 0x%08X ==' % HOOK_VA)
    w = NEW_HOOK
    chk(w >> 26 == 2, 'opcode = j (2), 实得 %d' % (w >> 26))
    tgt = (w & 0x3FFFFFF) << 2
    chk(tgt == CAVE_VA, 'j 目标 = %08X (期望 %08X)' % (tgt, CAVE_VA))
    chk((tgt >> 28) == ((HOOK_VA + 4) >> 28), 'j 目标与延迟槽同 256MB 区段')

    print('== 2. cave 体 0x%08X (%d 词) ==' % (CAVE_VA, len(CAVE)))
    for i, w in enumerate(CAVE):
        print('    +%02X  %08X' % (4 * i, w))
    subu, lui1, add1, lw, bne1, addi_at, bne2, lw_h, addi_h, bne3, nop1, lui2, jmp, nop2 = CAVE

    chk(subu == 0x0062B823, 'subu $s7, $v1, $v0 (与原指令逐位相同, 无条件先算原值)')
    chk(lui1 >> 26 == 0x0F and ((lui1 >> 16) & 31) == 8 and (lui1 & 0xFFFF) == 0x0059,
        'lui $t0, 0x0059')
    chk(add1 >> 26 == 9 and ((add1 >> 21) & 31) == 8 and ((add1 >> 16) & 31) == 8
        and s16(add1 & 0xFFFF) == 0x78C0, 'addiu $t0, $t0, 0x78C0')
    chk((((lui1 & 0xFFFF) << 16) + 0x78C0) == 0x005978C0,
        'lui+addiu 合成常量 = 0x%08X (期望 __vt__6RSHTML 0x005978C0)'
        % (((lui1 & 0xFFFF) << 16) + 0x78C0))
    chk(lw >> 26 == 0x23 and ((lw >> 21) & 31) == 0x15 and ((lw >> 16) & 31) == 1
        and s16(lw & 0xFFFF) == 0, 'lw $at, 0($s5)')
    chk(bne1 >> 26 == 5 and ((bne1 >> 21) & 31) == 1 and ((bne1 >> 16) & 31) == 8,
        'bne $at, $t0, ...')
    t1 = CAVE_VA + 0x10 + 4 + (s16(bne1 & 0xFFFF) << 2)
    chk(t1 == CAVE_VA + 0x30, 'bne#1 目标 = %08X (期望出口 j @%08X)' % (t1, CAVE_VA + 0x30))
    chk(addi_at >> 26 == 9 and ((addi_at >> 21) & 31) == 0 and ((addi_at >> 16) & 31) == 1
        and s16(addi_at & 0xFFFF) == 270, 'addiu $at, $zero, 270')
    chk(bne2 >> 26 == 5 and ((bne2 >> 21) & 31) == 3 and ((bne2 >> 16) & 31) == 1,
        'bne $v1, $at, ...')
    t2 = CAVE_VA + 0x18 + 4 + (s16(bne2 & 0xFFFF) << 2)
    chk(t2 == CAVE_VA + 0x30, 'bne#2 目标 = %08X (期望出口 j @%08X)' % (t2, CAVE_VA + 0x30))
    chk(lw_h >> 26 == 0x23 and ((lw_h >> 21) & 31) == 0x15 and ((lw_h >> 16) & 31) == 2
        and s16(lw_h & 0xFFFF) == 0x44, 'lw $v0, 0x44($s5)  (H)')
    chk(addi_h >> 26 == 9 and ((addi_h >> 21) & 31) == 0 and ((addi_h >> 16) & 31) == 1
        and s16(addi_h & 0xFFFF) == 190, 'addiu $at, $zero, 190')
    chk(bne3 >> 26 == 5 and ((bne3 >> 21) & 31) == 2 and ((bne3 >> 16) & 31) == 1,
        'bne $v0, $at, ...')
    t3 = CAVE_VA + 0x24 + 4 + (s16(bne3 & 0xFFFF) << 2)
    chk(t3 == CAVE_VA + 0x30, 'bne#3 目标 = %08X (期望出口 j @%08X)' % (t3, CAVE_VA + 0x30))
    chk(nop1 == 0 and nop2 == 0, '两个延迟槽 nop 全零')
    chk(lui2 >> 26 == 0x0F and ((lui2 >> 16) & 31) == 0x17 and (lui2 & 0xFFFF) == 0x7FFF,
        'lui $s7, 0x7FFF')
    chk(jmp >> 26 == 2 and ((jmp & 0x3FFFFFF) << 2) == 0x21CC94,
        'j 0x0021CC94 (回 DoWordWrap 的 $s1=$s7)')

    print('== 3. 执行流 (逐条模拟) ==')
    for name, this_vptr, W, B4, H in (
            ('命中: RSHTML + 270x190', 0x005978C0, 270, 0, 190),
            ('未命中 A: vptr!=RSHTML (菜单/对话框)', 0x005979E0, 270, 0, 190),
            ('未命中 B: W=400 (页面大标题)', 0x005978C0, 400, 0, 16),
            ('未命中 C: RSHTML 270x156 (简报正文)', 0x005978C0, 270, 0, 156),
            ('未命中 D: RSHTML 270x200 (假想 SF 变体)', 0x005978C0, 270, 0, 200)):
        v1, v0 = W, B4
        s7 = 0xDEADBEEF
        s7 = (v1 - v0) & 0xFFFFFFFF                       # +0x00 subu (无条件)
        t0 = (0x0059 << 16)                               # +0x04
        t0 = (t0 + 0x78C0) & 0xFFFFFFFF                   # +0x08
        at = this_vptr                                    # +0x0C
        taken1 = (at != t0)                               # +0x10
        at = 270                                          # +0x14 延迟槽
        if not taken1:
            taken2 = (v1 != at)                           # +0x18
            v0 = H                                        # +0x1C 延迟槽
            if not taken2:
                at = 190                                  # +0x20
                taken3 = (v0 != at)                       # +0x24
                if not taken3:
                    s7 = 0x7FFF << 16                     # +0x2C lui $s7
        sw = s7 if s7 < 0x80000000 else s7 - 0x100000000
        print('   %-40s → wrapW = 0x%08X (%d)' % (name, s7, sw))
    print('\n结论: %s' % ('全部通过' if ok else '★ 有不符项'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
