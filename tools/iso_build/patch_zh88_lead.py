# -*- coding: utf-8 -*-
r"""patch_zh88_lead.py — 把 DBCS lead 上界从 0xAE 抬到 0xAF（即 lead 可用到 0xAE）

## 语义澄清（重要，勿误读）
代码是 `sltiu $t1, lead, IMM`，即"lead < IMM 才算 DBCS"。
- 现役 IMM=**0xAE** ⇒ lead 只能是 `0xA1..0xAD`（13 个）
- 本补丁把 IMM 抬到 **0xAF** ⇒ lead 可用 `0xA1..0xAE`（14 个）
**所以"改 0xAE→0xAF"= 让 `0xAE` 成为合法 lead**（不是让 lead 变成 0xAF）。

## 为什么 0xAE 是最后一个空位
```
单字节汉字码占 0xAF..0xFE；0xAF 就是 "的"（全盘出现 1452 处）
0xAE 完全未被占用：7716 条文本按现役规则逐字符解析，以 0xAE 开头的 **0 处**
                  （0xAE 只作为 trail 出现 420 次）
⇒ lead ≥ 0xAF 会让 8425 个单字节 "的" 被吞 ⇒ **0xAF 是硬天花板**
   实测 GR_ZH93（IMM→0xB0）：113/281 帧不同，单字节 0xAF 调用 8425→0 ⇒ 灾难性错位
```

## 改动（**4 处**，不是 3 处）
全 `.text`（VA 0x100000..0x5DED00）扫 `sltiu ...,0xAE` 得 **4 处**：
```
0x416EE8  sltiu $9,  $5,  0xAE   [DrawString 取码]
0x417160  sltiu $9,  $8,  0xAE   [StringWidth 头]
0x41751C  sltiu $11, $10, 0xAE   [DoWordWrap 逐字]
0x5656A4  sltiu $12, $11, 0xAE   [StringWidth 尾 DBCS 计数]  ← 首版漏改！
```
**首版只改了前 3 处** ⇒ 第 4 处（`0x565670` 尾块里**独立重新解析整串**数 DBCS 字符数，
供 `(nChars-1)×tracking`）漏改**不报错**，只让宽度略偏：
真实机器码实测 `AE A1 + AE A2` 得 34（应 33）；8×`AE A1` 得 136（应 135）。
**本版已补齐 4 处。**

## 实测（4 处版，盘 = work/builds/GR_ZH92）
281/281 截图 sha256 **逐字节相同**；drawlog 68,886,326 B **逐字节相同** ⇒ **零回归**。

## 效果（并附现实约束）
```
lead 0xA1..0xAD (13) → 0xA1..0xAE (14)
码位空间 13×94 = 1222 → 14×94 = 1316   (剩 86 → 180)
```
⚠ **但"剩余 180"在字形层面是名义值** —— 86 个剩余槽里 **76 个的图集格位已被 76 个
单字节汉字字形占住**（一一对应无缝互锁），真正**立刻可用只有 10 个**
（`AD F5..AD FE`）。扩 lead 后新增 94 格里 **90 格自由**（4 格被 13px 保护字形记录挡住，
建议避开 `0xAE F6..F9`）。
⇒ 立刻可用 **10** → 扩 lead 后 **100** → 再迁走 76 个单字节字形 → **176~180**。
详见 `work/_dis/REPORT_CODEPOINT_EXPANSION.md`。

⚠ 本补丁**只扩码位空间**，不新增任何字形。新增字需要：
   1. 在字库纹理的空闲格里放字形
   2. 在 chars 表（`charset_compiled_zh16.json`）里登记新码位
   3. 重写文本使用新码位

## 用法
  python patch_zh88_lead.py <src_iso> <dst_iso>   (基底 = GR_ZH87)
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000

# (VA, 旧值, 新值, 说明)
# ★ 2026-10-05 修正: 补上漏掉的第 4 处 (0x5656A4)
#   全 .text (VA 0x100000..0x5DED00) 扫 `sltiu ...,0xAE` 得 **4 处**, 本补丁首版只列 3 处。
#   第 4 处 0x5656A4 在 `0x565670` 尾块里**独立重新解析整串**数 DBCS 字符数 t1
#   (供 `StringWidth` 的 `(nChars-1)×tracking` 项)。漏改**不报错**, 只是宽度略偏:
#     真实机器码实测 `AE A1 + AE A2` 得 34 (应 33);  8×`AE A1` 得 136 (应 135)。
#   证据: work/_dis/REPORT_CODEPOINT_EXPANSION.md §2; 4 处版 GR_ZH92 实测
#         281/281 截图 sha256 逐字节相同 + drawlog 68,886,326 B 逐字节相同 (零回归)。
PATCHES = [
    (0x416EE8, 0x2CA900AE, 0x2CA900AF, 'DrawString 取码 cave:    lead 上界 0xAE→0xAF'),
    (0x417160, 0x2D0900AE, 0x2D0900AF, 'StringWidth 头 cave:     lead 上界 0xAE→0xAF'),
    (0x41751C, 0x2D4B00AE, 0x2D4B00AF, 'DoWordWrap 逐字 cave:    lead 上界 0xAE→0xAF'),
    (0x5656A4, 0x2D6C00AE, 0x2D6C00AF, 'StringWidth 尾 DBCS 计数: lead 上界 0xAE→0xAF  ← 首版漏改'),
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
    total = 0
    with open(dst, 'r+b') as f:
        for va, old, new, desc in PATCHES:
            o = elf_off(va)
            f.seek(o)
            f.write(struct.pack('<I', new))
            f.seek(o)
            got = struct.unpack('<I', f.read(4))[0]
            assert got == new, '回读不符 @0x%06X' % va
            total += 1
    print('[fix ] %d 处已改写' % total)

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    diffs = [i for i in range(0, len(a)) if a[i] != b[i]]
    print('[chk ] 全盘差异字节 %d 个' % len(diffs))
    for va, old, new, _d in PATCHES:
        o = elf_off(va)
        n = sum(1 for k in range(4) if a[o + k] != b[o + k])
        print('      0x%06X: %d 字节 (ISO@0x%X)' % (va, n, o))

    print()
    print('  ⇒ lead 范围 0xA1..0xAE (14);  码位空间 14×94 = %d 槽' % (14 * 94))
    print('     剩余 %d ≥ 音译需求 175 ⇒ 缺口归零' % (14 * 94 - 1136))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
