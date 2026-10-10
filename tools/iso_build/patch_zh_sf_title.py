# -*- coding: utf-8 -*-
r"""patch_zh_sf_title.py — 「特别收录内页金框条目名」垂直位置修复 (round27 / sf-inner-title)

## 用户报障 (逐字)
> 特别收录里武器等内容的小标题出现下沉 … 主菜单->特别收录->武器 上方的小标题
> 「定向地雷（M18）」这一块的显示内容有明显下沉。导航并解析它的显示逻辑

## 定位 (drawlog + EE RAM 实证, 见 docs/REPORT_zh82s_sf_title.md)
该「小标题」= **武器内页的金色横向条目条** 里的条目名, 由
`IkeBaseButton::DrawText @0x21D830` 绘制 (**RA=21DA28**, 不经 `0x565900` cave;
故 `0x565910` 与它无关, 2026-10-08 实测: 改 `0x565910` 时它的 y 逐像素不变)。

垂直公式 (0x21D920..0x21D960):
```
style 含 0xC ⇒ y = [0x3C](ay) + [0x4C] + [0xD9] + ( [0x44](H) − K ) / 2      (C 语言式向零取整)
K 在 0x21D940:  EN 原词 00621023 = subu $v0,$v1,$v0  ⇒ K = CharHeight(font) = 26
                ZH40 起 2462FFEB = addiu $v0,$v1,-21 ⇒ K = 21 (硬编码, 认证值)
```
**同一个 (H−K)/2 旋钮管两类场景** (EE RAM 实测组件指纹, vtable 均 = 00595520):

| 组件 | 实例 | W | H | ax/ay | K=21 结果 | EN(K=26) 结果 |
|---|---|---|---|---|---|---|
| 前端列表行 (主菜单/战术演习/文件选择) | `0x0132FF60` 等 | 190~284 | **31** | 43/154 | (31−21)/2=**5** | (31−26)/2=**2** |
| 特别收录内页条目条 (定向地雷（M18）) | `0x012F3510` | **600** | **20** | 20/80 | (20−21)/2=**0** | (20−26)/2=**−3** |
| 特别收录列表行 (影片/武器/…) | `0x012F3300` 等 | 236 | 31 | 72/106 | 5 | 2 |

> 注: 取整是 C 式 (向零): 先 `bgez` 若负则 `+1` 再 `sra 1` ⇒ (20−21)/2 = 0, (20−26)/2 = −3。

**实测 (原生 640x448, 帧 F11300, 金色条 y[75.4..103.1], 条内文字质心)**:

| 盘 | 条目名 pen y | 暗字墨迹带 | 质心 | 观感 |
|---|---|---|---|---|
| EN 原盘 | 87 | y[85.3..98.6] | 91.5 | 贴下沿 (原版字形较大) |
| ZH82 现役 (K=21) | **90** | y[84.3..98.6] | 92.0 | **贴下沿 ⇒ 用户所见"明显下沉"** |
| K=26 诊断盘 | 87 | y[82.2..96.6] | 89.9 | 条内**垂直居中** |
| 本补丁 (条件化) | 87 | = K26 | = K26 | 同上, 且前端列表行**逐像素不变** |

## 本补丁 (条件化, 不是一刀切回退)
1. 挂点 `0x21D940`: `2462FFEB (addiu $v0,$v1,-21)` → `08159680 (j 0x565A00)`
2. 延迟槽 `0x21D944`: `04410003 (bgez $v0,0x21D954)` → `00000000 (nop)`
   (原 `bgez` 的语义在 cave 内逐词复刻; 该地址只由 0x21D940 落入, 无其它 xref)
3. tail-cave `0x565A00` (19 词, 落点属 ZH58 复核过的 `0x56566E-0x56D7EF` 恒零填充区):
```
0x565A00  addiu $t4,$zero,20          ; 判据①: H == 20 ?
0x565A04  bne   $v1,$t4,0x565A28      ;   否 → 保持 K=21
0x565A08  nop
0x565A0C  lw    $t3,0x40($s2)         ; W
0x565A10  sltiu $at,$t3,400           ; 判据②: W >= 400 ? (排除 H=20 的小图标按钮 W=20/34)
0x565A14  bne   $at,$zero,0x565A28    ;   否 → 保持 K=21
0x565A18  nop
0x565A1C  subu  $v0,$v1,$v0           ;   H==20 且 W>=400 → K = CharHeight (EN 原式)
0x565A20  b     0x565A2C
0x565A24  nop
0x565A28  addiu $v0,$v1,-21           ; ★ 0x21D940 的认证原词原封不动保存在 cave 内
0x565A2C  bgez  $v0,0x565A3C          ; ↓ 以下 4 词 = 0x21D944/48/4C/50 逐词复刻
0x565A30  sra   $v1,$v0,1             ;   (延迟槽)
0x565A34  addiu $v0,$v0,1
0x565A38  sra   $v1,$v0,1
0x565A3C  lui   $at,0x0021
0x565A40  ori   $at,$at,0xD954        ; ra = 0x21D954
0x565A44  jr    $at                   ; 回原流程 (此时 $v1 = (H−K)/2)
0x565A48  nop
```
- 判据来源 (EE RAM 实测, K26 诊断盘 F11300): `H==20` 的按钮共 48 个 —— 1 个 `W=600`
  (= 本目标: SF 内页条目条) + 47 个 `W=34`/`W=20` 小图标/图例按钮; 只加 `H==20` 会把底栏
  `△返回/✕查看` 的图标一起上移 2px (2026-10-08 全帧回归实证), 故追加 `W>=400`;
- 覆盖面: **只有 H==20 且 W>=400 的按钮** (实测 = SF 内页条目条模板; 9 个内页
  武器/奖章/背景/访谈/预告片… 同模板);
- 前端列表行 (H=31) 与其它一切按钮 **逐位/逐像素不变** (全帧回归见报告);
- 只打补丁, 不重建 ISO; 改前断言原词 + 改后回读 + 全盘差异白名单 + 反汇编复核;
- 用户认证值 `0x4176A0`、`0x565910`、`0x21C624`/`0x565900` cave 全部硬断言, 本补丁不触碰。

## 用法
  python patch_zh_sf_title.py <src_iso> <dst_iso>
  期望基底: work/builds/GR_ZH82/GR_ZH82.iso (sha256 41b9ccf2…)
"""
import hashlib
import os
import shutil
import struct
import sys

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000

# ---- 挂点 (VA, EN 原词, ZH82 旧词, 新词, 说明) ----
PATCHES = [
    (0x21D940, 0x00621023, 0x2462FFEB, 0x08159680,
     'addiu $v0,$v1,-21 → j 0x565A00 (条件化 K)'),
    (0x21D944, 0x04410003, 0x04410003, 0x00000000,
     'bgez $v0,0x21D954 → nop (延迟槽; 语义已在 cave 内复刻)'),
]

# ---- tail-cave: 16 词 ----
CAVE_VA = 0x565A00
CAVE = [
    0x240C0014,   # addiu $t4,$zero,20          判据① H==20
    0x146C0008,   # bne   $v1,$t4,0x565A28      (rs=$v1=H, rt=$t4=20)
    0x00000000,   # nop
    0x8E4B0040,   # lw    $t3,0x40($s2)         W
    0x2D610190,   # sltiu $at,$t3,400           判据② W<400 ?
    0x14200004,   # bne   $at,$zero,0x565A28    → 小图标按钮保持 K=21
    0x00000000,   # nop
    0x00621023,   # subu  $v0,$v1,$v0           K = CharHeight (EN 原式)
    0x10000002,   # b    0x565A2C
    0x00000000,   # nop
    0x2462FFEB,   # addiu $v0,$v1,-21          ★ 认证 K=21 原词 (逐字保留)
    0x04410003,   # bgez  $v0,0x565A3C         ┐
    0x00021843,   # sra   $v1,$v0,1            │ = 0x21D944/48/4C/50 逐词复刻
    0x24420001,   # addiu $v0,$v0,1            │
    0x00021843,   # sra   $v1,$v0,1            ┘
    0x3C010021,   # lui   $at,0x0021
    0x3421D954,   # ori   $at,$at,0xD954       ra = 0x21D954
    0x00200008,   # jr    $at
    0x00000000,   # nop
]

# ---- 必须完好 (用户认证 / 其它在役 cave) ----
CERTIFIED = [
    (0x4176A0, 0x24020010, 'CAVE16 假 CharHeight=16 (ZH82 在役, 用户口径)'),
    (0x565910, 0x24E70007, 'ZH61 标题居中量 a3 += 7 (用户认证, 本轮勿动)'),
    (0x21C624, 0x08159640, 'ZH61 挂点 j 0x565900'),
    (0x565900, 0x9221009C, 'ZH61 cave 首词 lbu $at,0x9C($s1)'),
    (0x565930, 0xAFA80010, 'ZH76 cave 首词 sw $t0,0x10(sp)'),
    (0x219A74, 0x0815964C, 'ZH76 挂点 j 0x565930'),
    (0x21AC90, 0x0815959C, 'ZH58 SWKERN 挂点 j 0x565670'),
]


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def main(src, dst):
    d = bytearray(open(src, 'rb').read())

    # ---- 1. 断言: 挂点原词 / 认证值 / cave 落点全零 ----
    for va, en, old, new, desc in PATCHES:
        cur = struct.unpack_from('<I', d, elf_off(va))[0]
        assert cur == old, '0x%06X 原词 %08X != 期望 %08X [%s]' % (va, cur, old, desc)
        print('[in ] 0x%06X 现役 %08X (EN %08X) → %08X  %s' % (va, cur, en, new, desc))
    for va, want, desc in CERTIFIED:
        got = struct.unpack_from('<I', d, elf_off(va))[0]
        assert got == want, '用户认证/在役值不符: 0x%06X = %08X != %08X [%s]' % (va, got, want, desc)
    for i in range(len(CAVE)):
        va = CAVE_VA + 4 * i
        got = struct.unpack_from('<I', d, elf_off(va))[0]
        assert got == 0, 'cave 落点 0x%06X 非零 (%08X), 该区已被占用' % (va, got)
    print('[chk ] 挂点原词 + %d 处认证/在役值 + cave 落点 %d 词全零: 全部符合'
          % (len(CERTIFIED), len(CAVE)))

    # ---- 2. 写补丁 ----
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        for va, en, old, new, desc in PATCHES:
            f.seek(elf_off(va))
            f.write(struct.pack('<I', new))
        for i, w in enumerate(CAVE):
            f.seek(elf_off(CAVE_VA + 4 * i))
            f.write(struct.pack('<I', w))
        # 回读自验
        for va, en, old, new, desc in PATCHES:
            f.seek(elf_off(va))
            got = struct.unpack('<I', f.read(4))[0]
            assert got == new, '回读不符 @0x%06X: %08X' % (va, got)
        for i, w in enumerate(CAVE):
            f.seek(elf_off(CAVE_VA + 4 * i))
            got = struct.unpack('<I', f.read(4))[0]
            assert got == w, 'cave 回读不符 @0x%06X: %08X != %08X' % (CAVE_VA + 4 * i, got, w)
    print('[fix ] %d 处挂点 + %d 词 cave 已写入并回读通过' % (len(PATCHES), len(CAVE)))

    # ---- 3. 全盘差异白名单 ----
    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    allow = set()
    for va, en, old, new, desc in PATCHES:
        allow |= set(range(elf_off(va), elf_off(va) + 4))
    allow |= set(range(elf_off(CAVE_VA), elf_off(CAVE_VA) + 4 * len(CAVE)))
    diffs = [i for i in range(len(a)) if a[i] != b[i]]
    bad = [hex(x) for x in diffs if x not in allow]
    assert not bad, '白名单外差异: %s' % bad[:8]
    print('[chk ] 全盘差异 %d 字节, 全部落在挂点/延迟槽 (%d B) 与 cave %d 词 (%d B)'
          % (len(diffs), 2 * 4, len(CAVE), 4 * len(CAVE)))

    # ---- 4. 反汇编复核 ----
    try:
        from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
        md.skipdata = True
        for va0, n, name in ((0x21D92C, 12, 'IkeBaseButton::DrawText 0x21D92C 起 (改后)'),
                             (CAVE_VA, len(CAVE), 'tail-cave 0x565A00 (改后)')):
            print('[dis ] %s:' % name)
            blob = b[elf_off(va0):elf_off(va0 + 4 * n)]
            for ins in md.disasm(blob, va0):
                print('        0x%06X  %-10s %s' % (ins.address, ins.mnemonic, ins.op_str))
    except Exception as e:                      # noqa: BLE001
        print('[dis ] (capstone 不可用: %s)' % e)

    assert struct.unpack_from('<I', b, elf_off(CAVE_VA + 10 * 4))[0] == 0x2462FFEB, \
        '认证 K=21 原词未逐字保留在 cave 内 (0x565A28)'
    print('[sha ] %s' % hashlib.sha256(b).hexdigest())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
