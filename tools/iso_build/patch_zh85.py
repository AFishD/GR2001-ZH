# -*- coding: utf-8 -*-
r"""patch_zh85.py — 特别收录金框标题 + 内页大标题垂直位置修复 (GR_ZH85)

## 用户报障
特别收录 → 武器/奖章/背景/访谈/预告片:
  - 金框内**条目名下沉贴下沿** (如 "定向地雷（M18）")
  - 内页**顶部大标题下沉** (如 "武器")

## 根因 (双盘反汇编对比, work/_dis/REPORT_wrap_and_title.md)

### 路径 1: 金框栏目行 / 金框条目名 (`RA=21DA28`, `IkeBaseButton::DrawText @0x21D830`)
居中公式 `y = ay + comp[0x4C] + comp[0xD9] + (H − K)/2`:
```
EN 原盘:  0021D940  subu  $v0, $v1, $v0    ; K = CharHeight (RSFont::CharHeight @0x21ACD0)
ZH84:     0021D940  addiu $v0, $v1, -21    ; K 被**硬编码成 21**
```
- 该分支上方 `0021D934 jal CharHeight` → EN 把返回值当 K 用；
- EN 实测 CharHeight = **26** (FontDefinition+0xC, large/default 面)；
- 中文盘硬编码 **21** ⇒ 居中量 `(H−21)/2` 比 EN 的 `(H−26)/2` **少 2.5 → 文字下移 ~3px**
  (实测: SF 列表行 EN 'Weapons' y=171 / ZH '武器' y=174; 内页金框 EN y=87 / ZH y=90;
   金框内墨迹下留白 0px = 贴下沿)。
**修法**: `0x21D940` 由 `addiu $v0,$v1,-21` 还原为 EN 的 `subu $v0,$v1,$v0`。

### 路径 2: 内页顶部大标题 (`RA=21C62C`, `RSTextComponent::DrawTheString`)
- 该组件 `comp[0x1C]=1` ⇒ `StyleIsSet(3)/(0xC)/(8)` 全假 ⇒ **不走 ComputeDrawXY 居中分支**
  (故 ZH83 改的 `0x4176A0` cave 对它**天然无效**)；
- 其 +7px 来自 **zh7 绘层 cave `0x565900`**: `lbu comp[0x9C]; if ==5 → a3 += 7`
  ⇒ y = 18+7 = 25，EN = 18。
```
00565900  lbu   $at, 156($s1)      ; comp[0x9C]
00565904  addiu $t4, $zero, 5
00565908  bne   $at, $t4, 0x565914
0056590C  ...
00565910  addiu $a3, $a3, 7        ; ★ +7, 改为 nop 即上移 7px
```
**修法**: `0x565910` 的 `0x24E70007` → `0x00000000` (nop)。
- 覆盖面: SF 内页 10 个 studio 的大标题模板一致(武器与奖章已双实证 y=25 vs EN 18)；
  金框 10 行模板亦一致(W=236/H=31/ax=72)。

## 用法
  python patch_zh85.py <src_iso> <dst_iso>   (基底 = GR_ZH84)
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000

PATCHES = [
    # (VA, 旧值, 新值, 说明)
    (0x21D940, 0x2462FFEB, 0x00621023,
     'addiu $v0,$v1,-21 → subu $v0,$v1,$v0 (恢复 K=CharHeight, 金框文字上移 ~3px)'),
    (0x565910, 0x24E70007, 0x00000000,
     'addiu $a3,$a3,7 → nop (内页大标题上移 7px, 与 EN 对齐)'),
]


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def main(src, dst):
    sd = open(src, 'rb').read()
    for va, old, new, desc in PATCHES:
        o = elf_off(va)
        cur = struct.unpack_from('<I', sd, o)[0]
        assert cur == old, '0x%06X 原值 %08X != 期望 %08X' % (va, cur, old)
        print('[in ] 0x%06X: %08X  %s' % (va, cur, desc))

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        for va, old, new, desc in PATCHES:
            o = elf_off(va)
            f.seek(o)
            f.write(struct.pack('<I', new))
            f.seek(o)
            got = struct.unpack('<I', f.read(4))[0]
            assert got == new, '回读不符 @0x%06X' % va
    print('[fix ] %d 处已改写' % len(PATCHES))

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    diffs = [i for i in range(0, len(a)) if a[i] != b[i]]
    exp = {(elf_off(va) + k) for va, _o, _n, _d in PATCHES for k in range(4)}
    print('[chk ] 全盘差异字节 %d 个' % len(diffs))
    # 统计每个补丁实际变化的字节数 (立即数差异可能只改低字节)
    for va, old, new, _d in PATCHES:
        o = elf_off(va)
        n = sum(1 for k in range(4) if a[o + k] != b[o + k])
        print('      0x%06X: %d 字节变化 (%08X → %08X)' % (va, n, old, new))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
