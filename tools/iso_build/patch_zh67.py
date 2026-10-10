# -*- coding: utf-8 -*-
r"""patch_zh67.py — GR_ZH67 = ZH66 + 帮助条垂直居中补偿 (style-0x52 手术 cave)

问题 (2026-10-03 用户报障): 主菜单等界面底部滚动说明条文字贴显示区域顶部而非居中。
根因: 帮助条组件 (RSTextComponent, §五.7 身份本轮锁定: style=0x52, W=250 H=20,
ay=419, 每帧 x−2 横滚) 无垂直居中 style 位 → 默认顶锚 ay。EN 原版 26px 行盒内墨迹
自然落条带中部 (实测 EN 墨 [389,396] 居中于 H=20 条带); 我们 16px 四边形顶锚 →
墨迹 [383,398] 贴顶 (顶隙 2 vs EN 8)。同 ZH66 leading 机理的组件级体现。

修复 (ELF 手术, 仅动 style-0x52 族 — 其余组件全为 0x53 不受影响):
  hook 0x21CA50: sw v1,0xEC(a0) → j 0x565730
    (延迟槽 0x21CA54 lbu v1,0x108 先执行, 后续 bne v1 保真; v1 原值仅被替换掉的 sw 消费)
  cave 0x565730 (ZH58 六转储验证安全区 0x565670-0x5658B0 内, SWKERN 止于 0x56571C):
    y = [a0+0x3C] + [a0+0x4C]          (与原指令链 0x21CA44-4C 严格等价重算)
    if (style([a0+0x14]) & 0xFF) == 0x52: y += 2
    [a0+0xEC] = y;  j 0x21CA58
  寄存器: 仅用 t0/t1/t2 (该边界处调用者保存死寄存器, 后续 0x21CA60 jal 亦会清)

用法: python patch_zh67.py <src_iso> <dst_iso>   (基底 = GR_ZH66)
"""
import shutil
import struct
import sys

ELF_LBA = 295
HOOK_VA, HOOK_OLD, HOOK_NEW = 0x21CA50, 0xAC8300EC, 0x081595CC   # sw v1,0xEC(a0) → j 0x565730
CAVE_VA = 0x565730
CAVE = [
    0x8C88003C,  # lw   t0, 0x3C(a0)
    0x8C8A004C,  # lw   t2, 0x4C(a0)
    0x010A4021,  # addu t0, t0, t2        ; y = 0x3C + 0x4C (等价原链)
    0x8C890014,  # lw   t1, 0x14(a0)      ; style
    0x312900FF,  # andi t1, t1, 0xFF
    0x240A0052,  # addiu t2, zero, 0x52
    0x152A0002,  # bne  t1, t2, +2 → 0x565754
    0x00000000,  # nop
    0x25080002,  # addiu t0, t0, 2        ; style==0x52: +2
    0xAC8800EC,  # sw   t0, 0xEC(a0)      ; 汇合写回
    0x08087296,  # j    0x21CA58
    0x00000000,  # nop
]


def rdelf(f, va):
    f.seek(ELF_LBA * 2048 + 0x80 + (va - 0x100000))
    return struct.unpack('<I', f.read(4))[0]


def main(src, dst):
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        cur = rdelf(f, HOOK_VA)
        assert cur == HOOK_OLD, f'0x{HOOK_VA:X} 现值 0x{cur:08X} != 0x{HOOK_OLD:08X} (非 ZH66 基底?)'
        for i in range(len(CAVE)):
            assert rdelf(f, CAVE_VA + 4 * i) == 0, f'cave 区 0x{CAVE_VA+4*i:X} 非零'
        f.seek(ELF_LBA * 2048 + 0x80 + (HOOK_VA - 0x100000))
        f.write(struct.pack('<I', HOOK_NEW))
        f.seek(ELF_LBA * 2048 + 0x80 + (CAVE_VA - 0x100000))
        f.write(b''.join(struct.pack('<I', w) for w in CAVE))
        assert rdelf(f, HOOK_VA) == HOOK_NEW
        for i, w in enumerate(CAVE):
            assert rdelf(f, CAVE_VA + 4 * i) == w
    # 全盘 diff: 差异词恰 = hook 1 词 + cave 非零词 (nop 与零区相同无差异)
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, words = 0, set()
    ha, ca = ELF_LBA*2048+0x80+(HOOK_VA-0x100000), ELF_LBA*2048+0x80+(CAVE_VA-0x100000)
    while True:
        ca_, cb_ = a.read(1 << 20), b.read(1 << 20)
        if not ca_:
            break
        for i in range(len(ca_)):
            if ca_[i] != cb_[i]:
                words.add((pos + i) & ~3)
        pos += len(ca_)
    a.close(); b.close()
    expect = {ha} | {ca + 4*k for k, w in enumerate(CAVE) if w != 0}
    assert words == expect, f'差异词集不符: 多出 {sorted(hex(x) for x in words-expect)} 缺少 {sorted(hex(x) for x in expect-words)}'
    print(f'[patch] hook 0x{HOOK_VA:X} + cave 0x{CAVE_VA:X} (12 词, 其中 {len(expect)-1} 非零) 写入; 差异词集精确吻合 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
