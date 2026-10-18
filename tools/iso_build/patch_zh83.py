# -*- coding: utf-8 -*-
r"""patch_zh83.py — 界面文字垂直位置补偿: 恢复 RSTextComponent 居中量 (GR_ZH83)

## 用户报障 (5 处界面文字垂直偏移)
原字库 26px → 统一换为 16px+4bit 扩容字库, **但文字坐标没做补偿**, 导致各界面文字在
固定框/条带内的垂直位置偏上或偏下:
  1. 主菜单→训练/战术演习: 右侧"训练标题"在框内**下对齐边缘**;
  2. 主菜单→战术演习→练习x: 右上角关卡名**靠上**, 顶到橙带上沿;
  3. 主菜单→特别收录→武器/奖章/背景/访谈: 上方**条目名称下偏到边缘**; 左下方介绍**换行错乱**;
  4. 主菜单→特别收录→预告片: 同上(条目名称下偏);
  5. 主菜单→选项→控制器: 左右按键说明**左居中/右靠下**, 且左右距边缘不一致。

## 根因 (字节级 + 反汇编确证, 见 work/_dis/report_A_B_offsets.md)
`RSTextComponent::ComputeDrawXY @0x21CA20` 负责把文字在组件框内做**垂直居中**:
    EN 原逻辑: y(字段+236) = [60] + [76] + ([68] − CharHeight)/2,  CharHeight = 26 (原字库)
中文盘 (zh16 换字库时) 做了三处改动:
    - 0x21CA50 → j 0x565730     (cave: y = [60]+[76], 且 style==0x52 时再 +4)
    - 0x21CB28  bnel 目标 0x21CB3C → 0x21CC08   (**跳过居中块**)
    - 0x21CB30 → jal 0x4176A0   (cave: `v0 = 16; jr $ra` → **CharHeight 硬编码 16**)
⇒ 居中量少算 (26−16)/2 = **5 px** → 该分支文字整体**下偏 5 px**。
   实测印证 (子代理双盘同帧量化): 界面A 中文墨迹底边比英文**低 3 px**, 下留白 5→2 px。

## 本补丁
把 cave `0x4176A0` 的硬编码字高 **16 → 20**:
    - 居中量由 ([68]−16)/2 变为 ([68]−20)/2 → 文字**上移 2 px**;
    - 20 是折中值: 完全对齐英文下留白需 21 (上移 2.5px), 但 20 更能兼顾"框内视觉居中"
      (中文无降部、CJK 全高 14px, 原英文的降部留白对中文是多余空间);
    - 只改该 cave 立即数, **不动任何逻辑分支**, 风险最低。

## 用法
  python patch_zh83.py <src_iso> <dst_iso>   (基底 = GR_ZH82)
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
CAVE_VA = 0x4176A0                     # addiu $v0, $zero, 16 ; jr $ra
OLD_VAL, NEW_VAL = 16, 20


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def main(src, dst):
    sd = open(src, 'rb').read()
    o = elf_off(CAVE_VA)
    cur = struct.unpack_from('<I', sd, o)[0]
    want = (0x09 << 26) | (0 << 21) | (2 << 16) | OLD_VAL       # addiu $v0,$zero,16
    assert cur == want, 'cave 首指令不符: %08X (期望 %08X)' % (cur, want)
    nxt = struct.unpack_from('<I', sd, o + 4)[0]
    assert nxt == 0x03E00008, 'cave 第 2 指令不是 jr $ra: %08X' % nxt
    print('[in ] 0x%06X: addiu $v0,$zero,%d ; jr $ra' % (CAVE_VA, OLD_VAL))

    new = (0x09 << 26) | (0 << 21) | (2 << 16) | NEW_VAL
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(o)
        f.write(struct.pack('<I', new))
        f.seek(o)
        got = struct.unpack('<I', f.read(4))[0]
        assert got == new, '回读不符 %08X' % got
    print('[fix ] 0x%06X: addiu $v0,$zero,%d  (字高 16→20, 居中量 +2px)' % (CAVE_VA, NEW_VAL))

    # 完整性: 尺寸不变 / 只改这一处 (16→20 只影响立即数低字节 → 恰好 1 字节)
    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    diffs = [i for i in range(0, len(a)) if a[i] != b[i]]
    print('[chk ] 全盘差异字节 %d 个: %s' % (len(diffs), [hex(x) for x in diffs[:6]]))
    assert len(diffs) == 1 and diffs[0] == o, '差异不止一处! (期望仅有 0x%X)' % o
    assert a[o] == OLD_VAL and b[o] == NEW_VAL, '差异值不符: %d→%d' % (a[o], b[o])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
