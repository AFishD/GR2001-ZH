# -*- coding: utf-8 -*-
r"""patch_zh_title_center.py — 子界面标题垂直居中修复 (GR_ZH82_T / 第 26 轮)

## 用户报障
主菜单几乎每一项进入后, 界面左上角显示的**子界面标题上偏**; 早期版本已把它调到
垂直居中, 现在又上偏了。

## 历史与根因 (逐字节实证)
1. **GR_ZH61** (`work/zh16b/subagent_l1panel3/build_zh61.py`, 提交 0bcbeb34) 引入了
   "标题垂直居中"补偿, 由 1 挂点 + 13 词 tail-cave 组成:
   - 挂点 `0x21C624`: `jal 0x219EB0` (DrawString) → `j 0x565900`;
   - cave `0x565900`(13 词): `lbu $at,0x9C($s1)` (组件 fontID) == 5 (标题档) 时
     `$a3 += 7`, 然后 `ra = 0x21C62C`、跳 `0x219EB0`。
   - 依据: 标题组件模板 (3 实例同参) `fontID(+0x9C)=5`、`W=400 H=16`、
     锚点 `(+0x38,+0x3C)=(33,18)`; EN 用 26px 行盒 (墨迹 y24-42, 中心 33),
     中文 16px 满格字库墨迹自笔位 +0 起画 (y18-31, 中心 24.5) ⇒ 同一笔位下
     中文墨迹**偏高 ~7.5px**; +7 后中文墨迹 y25-38 (中心 31.5), 与 EN 墨心
     (33) 及标题栏 (y18-46, 中心 32) 对齐 ⇒ **垂直居中** (用户认证状态)。
2. **GR_ZH85** (`tools/iso_build/patch_zh85.py`, 第 2 条补丁) 为了对齐
   "特别收录→内页大标题"的**笔位**(EN pen y=18 vs ZH pen y=25) 把
   `0x565910` 的 `addiu $a3,$a3,7` **改成了 nop** —— 该判据比的是 drawlog 笔位,
   而 EN 的笔位 18 之后还有 26px 行盒的上留白 (其墨迹实际从 y24 起) ⇒ 判据有误。
   后果: 全部 `fontID==5` 子界面标题 (主菜单每一项进入后的左上角标题、特别收录
   各内页大标题) 一律回落到笔位 y=18 ⇒ **上偏 7px**。

现役盘 `work/builds/GR_ZH82/GR_ZH82.iso` 实测: 挂点 `0x21C624 = 08159640 (j 0x565900)`
**在役**; cave 主体 (lbu/addiu/bne + ra=0x21C62C + jr 0x219EB0) **完整**;
只有 `0x565910` 被 NOP 掉 ⇒ 本补丁**只还原这一个词**。

## 本补丁
```
0x565910  00000000 (ZH85 误 NOP)  →  24E70007  addiu $a3,$a3,7   (恢复 ZH61 的居中量)
```
- 覆盖面: `fontID(comp+0x9C)==5` 的 DrawTheString 路径 (页面大标题族);
  其它 fontID 走 bne 跳过, **逐位不变**;
- 不动 `0x21D940` (用户认证 K=21, 金框/列表居中) 与 `0x4176A0` (CAVE16 假 CharHeight=16),
  脚本内对这两处加硬断言 (值不符即报错, 防止再被覆盖);
- 不动 `0x565930` (它是 ZH76 命令面板 cave 的首词, 同时充当本 cave 尾跳的延迟槽);
- 铁律: 只打补丁, 不重建 ISO; 改前断言原词, 改后回读自验 + 全盘差异白名单。

## 用法
  python patch_zh_title_center.py <src_iso> <dst_iso>
  期望基底: work/builds/GR_ZH82/GR_ZH82.iso (sha256 6127a582…)
"""
import hashlib
import shutil
import struct
import sys

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000

# ---- 目标 ----
VA = 0x565910
EN_WORD = 0x00000000                     # EN 盘该区为死零填充
OLD_WORD = 0x00000000                    # ZH82 现状 = patch_zh85 写入的 nop
NEW_WORD = 0x24E70007                    # addiu $a3,$a3,7  (ZH61 的标题居中量, 用户认证)

# ---- ZH61 cave 结构断言 (整段必须完好, 只有 0x565910 被 NOP) ----
HOOK_VA, HOOK_WANT = 0x21C624, 0x08159640        # j 0x565900
CAVE_HEAD = [
    (0x565900, 0x9221009C, 'lbu $at,0x9C($s1)   ; fontID'),
    (0x565904, 0x240C0005, 'addiu $t4,$zero,5'),
    (0x565908, 0x142C0002, 'bne $at,$t4,+2      ; 非标题档直接跳过'),
    (0x56590C, 0x00000000, 'nop                 ; 延迟槽'),
    (VA,      OLD_WORD,   'addiu $a3,$a3,7 → ZH85 被 NOP (本补丁还原)'),
    (0x565914, 0x00000000, 'nop'),
    (0x565918, 0x3C010021, 'lui $at,0x0021'),
    (0x56591C, 0x3421C62C, 'ori $at,$at,0xC62C   ; ra = 0x21C62C'),
    (0x565920, 0x0020F825, 'or $ra,$at,$zero'),
    (0x565924, 0x3C010021, 'lui $at,0x0021'),
    (0x565928, 0x34219EB0, 'ori $at,$at,0x9EB0   ; DrawString'),
    (0x56592C, 0x00200008, 'jr $at'),
]
ZH76_CAVE_HEAD = (0x565930, 0xAFA80010)  # sw $t0,0x10(sp) — ZH76 cave 首词, 也是本 cave 尾跳延迟槽
# ---- 用户认证值 (本补丁绝不触碰) ----
CERTIFIED = [
    (0x21D940, 0x2462FFEB, 'IkeBaseButton style-0xC 盒居中 K=21 (ZH40 用户认证)'),
    (0x4176A0, 0x24020010, 'CAVE16 假 CharHeight=16 (ZH82 在役值)'),
]


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def main(src, dst):
    d = bytearray(open(src, 'rb').read())
    orig = bytes(d)

    # ---- 1. 原词备份 + 断言 ----
    o = elf_off(VA)
    cur = struct.unpack_from('<I', d, o)[0]
    print('[bak ] 0x%06X 原词 %08X (备份 %s)' % (VA, cur, dst + '.bak4'))
    open(dst + '.bak4', 'wb').write(struct.pack('<I', cur))
    assert cur == OLD_WORD, '0x%06X 原词 %08X != 期望 %08X (基底不是 GR_ZH82?)' % (VA, cur, OLD_WORD)

    hook = struct.unpack_from('<I', d, elf_off(HOOK_VA))[0]
    assert hook == HOOK_WANT, '0x%06X = %08X != %08X (ZH61 挂点不在役)' % (HOOK_VA, hook, HOOK_WANT)
    for va, want, desc in CAVE_HEAD:
        got = struct.unpack_from('<I', d, elf_off(va))[0]
        assert got == want, 'cave 0x%06X = %08X != %08X  [%s]' % (va, got, want, desc)
    va76, w76 = ZH76_CAVE_HEAD
    got76 = struct.unpack_from('<I', d, elf_off(va76))[0]
    assert got76 == w76, '0x%06X = %08X != %08X (ZH76 cave 首词, 勿动)' % (va76, got76, w76)
    for va, want, desc in CERTIFIED:
        got = struct.unpack_from('<I', d, elf_off(va))[0]
        assert got == want, '用户认证值被改动: 0x%06X = %08X != %08X  [%s]' % (va, got, want, desc)
    print('[chk ] ZH61 挂点 + cave 12 词 + ZH76 cave 首词 + 2 处用户认证值: 全部符合')

    # ---- 2. 写新词 ----
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(o)
        f.write(struct.pack('<I', NEW_WORD))
        f.seek(o)
        got = struct.unpack('<I', f.read(4))[0]
        assert got == NEW_WORD, '回读不符 %08X' % got
    print('[fix ] 0x%06X: %08X → %08X  addiu $a3,$a3,7 (子界面标题下移 7px 回垂直居中)'
          % (VA, OLD_WORD, NEW_WORD))

    # ---- 3. 全盘差异白名单 (仅这 4 字节) ----
    b = open(dst, 'rb').read()
    assert len(orig) == len(b), 'ISO 尺寸变化'
    diffs = [i for i in range(len(orig)) if orig[i] != b[i]]
    allow = set(range(o, o + 4))
    bad = [hex(x) for x in diffs if x not in allow]
    assert not bad, '出现白名单外差异: %s' % bad[:8]
    print('[chk ] 全盘差异 %d 字节, 全部落在 0x%X-0x%X (仅本补丁目标词)' % (len(diffs), o, o + 3))
    assert sorted(diffs) == [o, o + 2, o + 3], \
        '期望恰好 3 字节变化 (00 00 00 00 → 07 00 E7 24)' + str(diffs[:8])
    assert orig[o] == 0x00 and b[o] == 0x07, '低位不符: %02X→%02X' % (orig[o], b[o])
    assert orig[o + 1] == 0x00 and b[o + 1] == 0x00, '第 2 字节不应变'
    assert orig[o + 2] == 0x00 and b[o + 2] == 0xE7, '第 3 字节不符'
    assert orig[o + 3] == 0x00 and b[o + 3] == 0x24, '第 4 字节不符'

    # ---- 4. 反汇编回验 (capstone; 不可用则打印原始词) ----
    blob = b[elf_off(0x565900):elf_off(0x565930)]        # 12 词; 尾跳延迟槽 0x565930 归 ZH76 cave, 不在本段
    words = struct.unpack_from('<12I', blob)
    try:
        from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
        print('[dis ] cave 0x565900-0x56592C (改后, 12 词; 延迟槽 0x565930 = ZH76 cave 首词 0xAFA80010):')
        for ins in md.disasm(blob, 0x565900):
            print('       0x%06X  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
    except Exception as e:                                             # noqa: BLE001
        print('[dis ] (capstone 不可用: %s) 12 词: %s' % (e, ' '.join('%08X' % w for w in words)))
    assert words[4] == NEW_WORD, '反汇编源词校验失败'
    print('[sha ] %s' % hashlib.sha256(b).hexdigest())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
