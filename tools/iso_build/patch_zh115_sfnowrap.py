# -*- coding: utf-8 -*-
r"""patch_zh115_sfnowrap.py — **只对「特别收录」介绍框**关闭引擎自动折行 (GR_ZH115)

## 用户需求 (原话)

> **只修改特别收录部分的自动换行** 我已经手动调整过译文的翻译断句处

即: 「特别收录」介绍框里的 `{br}` / `{p}`(由 CSV 的 `{WRAP}` / 空行注入) 必须是
**唯一**的换行手段; 其余界面 (主菜单 / 对话框 / 简报 / 载入 …) 的自动折行**一字不动**。

## 为什么不是 `patch_zh112_noautowrap.py` 那把全局钥匙

同事的 ZH112 把 `0x21CC90` 的 `subu` 直接换成 `lui $s7,0x7FFF` —— 语义对, 但**范围是全球**:
DoWordWrap 的 4 个调用点 (`RSHTML::CreateStrings` ×3 / `RSTextComponent::SetText` ×1)
全部命中 ⇒ 语言表 255 条长段 (简报/任务介绍) 与 75 条短条目**同时失去折行**。
本轮把它**限定到组件级**。

## 判定条件: `comp->vptr == __vt__6RSHTML && comp[0x40] == 270 && comp[0x44] == 190`

三条都来自实测, 不是猜的:

1. **`__vt__6RSHTML` (0x005978C0)** —— 组件类型判据。
   `CreateComponent__Fi @0x2EE6A0` 实测: `type 6 → __ct__15RSTextComponentFv` (268 B),
   `type 9 → __ct__6RSHTMLFv` (280 B); `__ct__6RSHTML` 全 ELF 只有一个调用点 (0x2EE850)。
   主菜单/对话框/按钮走 type 6 ⇒ vptr ≠ 0x005978C0 ⇒ 天然不命中。
   **地址与构建无关**(数据段静态地址; GR_ZH98/105/109/111 四代实盘 RAM 实测同值)。

2. **`comp[0x40] == 270`** —— 「特别收录介绍框」的标定宽度
   (`docs/REPORT_wrap_and_title.md` §1.1; 本轮在 GR_ZH98/111/115 的 EE RAM 转储里复核同值)。

3. **`comp[0x44] == 190`** —— 「特别收录介绍框」的标定高度。**这条是第一轮实机抓出来的**:
   只判 1+2 时, 简报正文(`@01304E10`, W=270 **H=156**)也命中, 简报页折行被关掉、文本溢出到地图区。
   实测: 特别收录每个内页的介绍框都是 **270×190**; 简报正文框是 **270×156**。

**为什么不能用组件地址**: zh84 时代报的是 `COMP=0x012F4960`, 而 GR_ZH98/105/109/111 实测是
`0x0124A6A4` —— 实例地址**随构建漂移**(堆/池布局), 写死地址会在下一次重建时静默失效。

## 落点与语义 (1 个 ELF 词挂点 + 36 B cave)

```
0x21CC90 : 0062B823  subu $s7,$v1,$v0      ->  0815966A  j 0x005659A8
0x21CC94 : 72E08E28  move $s1,$s7          (不动: 它成了 j 的延迟槽, 见下)
```

**延迟槽说明 (本补丁的关键细节)**: `j` 在 0x21CC90, 它的延迟槽 = 0x21CC94
(`move $s1,$s7`)。延迟槽**先**执行 (此时 $s7 还是旧值, 无副作用), 然后进 cave;
cave 把 $s7 算对之后 **跳回 0x21CC94 再执行一次** ⇒ $s1 = 正确预算。
`move` 是幂等的寄存器复制 (`0x7080AE28` = 函数序言里的 `move $s5,$a0` 已独立证明
本作这条"未解码"指令就是 `move rd,rs`), double-execute 安全。

cave 体 (0x5659A8..0x5659DB, 14 词):

```
0x5659A8  0062B823  subu  $s7, $v1, $v0       ; ★ 原指令: 无条件先按原语义算好
0x5659AC  3C080059  lui   $t0, 0x0059
0x5659B0  250878C0  addiu $t0, $t0, 0x78C0     ; t0 = 0x005978C0 (必须在比较之前算完)
0x5659B4  8EA10000  lw    $at, 0($s5)          ; vptr
0x5659B8  14280007  bne   $at, $t0, +7         ; 非 RSHTML → 出口(保留原 wrapW)
0x5659BC  2401010E  addiu $at, $zero, 0x10E    ; 270 (延迟槽)
0x5659C0  14610005  bne   $v1, $at, +5         ; W != 270 → 出口(保留原 wrapW)
0x5659C4  8EA20044  lw    $v0, 0x44($s5)       ; (延迟槽) v0 = H
0x5659C8  240100BE  addiu $at, $zero, 190      ; 190
0x5659CC  14410002  bne   $v0, $at, +2         ; H != 190 → 出口(保留原 wrapW)
0x5659D0  00000000  nop                        ; (延迟槽)
0x5659D4  3C177FFF  lui   $s7, 0x7FFF          ; ★ 命中: wrapW = 0x7FFF0000 ≈ 2.1e9
0x5659D8  08087325  j     0x0021CC94           ; 出口/回 DoWordWrap (重新 $s1 = $s7)
0x5659DC  00000000  nop                        ; (j 的延迟槽, 本来就是 0, 不写)
```

**为什么必须有 `H == 190` 这一条（本轮实机抓出来的）**：第一版只判
`vptr==RSHTML && W==270`，结果**把简报正文也关了折行**——
简报页 `@01304E10` 实测 `W=270`、**`H=156`**、`ay=78`，行数 27 → 7（文本溢出到地图区，实拍见 §6.6）。
而特别收录介绍框在 GR_ZH98/111/115 的**每一个实测内页**上都是 **`H=190`**：

| 屏 | 组件 | W,H | 行数 |
|---|---|---|---|
| SF 开发访谈 1（内页） | `@0124A6A4` / `@0124B650` | 270,**190** | 117（= CSV 117 行） |
| SF 奖章（内页） | `@0124B650` | 270,**190** | 11（= CSV 11 行） |
| SF 列表页（影片/…/访谈/预告片） | 无 RSHTML 带多行 | — | — |
| **战术演习简报页** | `@01304E10` | 270,**156** | 27 |

语义: 命中 ⇒ wrapW ≈ 21 亿 ⇒ 预算永不 < 0、硬断闸门 (`slt $s7,tokw`) 永不成立
⇒ `RSHTML::CreateStrings` 按 `{br}`/`{p}` 切出的**每段恰好 1 行** ⇒ 换行只可能来自盘上标签。
未命中 ⇒ 延迟槽里的 `subu` 已把 $s7 算成**原值** `comp[0x40] − comp[0xB4]` ⇒ 逐位等价原路径。

$at/$t0 都是调用者可破坏的临时寄存器; DoWordWrap 本体全程不使用 $t0, $at 在 0x21CC94 处不活跃。

## cave 落点安全性 (四重自检, 脚本内置 + 离线已跑)

`0x5659A8..0x5659D8` 属既有恒零区 `0x565930-0x565C00` 的未用延伸段:

| 检查 | 结果 |
|---|---|
| ① ELF 静态全零 (48 B) | ✓ |
| ② 全 ELF 无 `j`/`jal` 以区间内地址为目标 | ✓ 0 处 |
| ③ 全 ELF 无 4 字节字面量落在区间 (9,363,433 词全扫) | ✓ 0 处 |
| ④ **68 份 EE RAM 转储**该区间全零 (含任务/简报/小队/开机/特别收录各族) | ✓ |

## 回退

`--revert` 把 0x21CC90 换回 `0x0062B823`、把 cave 9 词清零; 或拿上一代盘重建。
本补丁只在 ISO 的 ELF 区原位覆写, 不改数据容器/条目表/文件大小。

## 用法

    python tools/iso_build/patch_zh115_sfnowrap.py <src.iso> <dst.iso> [--report <json>]
                                                     [--dry-run] [--revert] [--allow-vt-mismatch]
"""
import argparse
import hashlib
import json
import mmap
import os
import shutil
import struct
import sys

ELF_LBA = 295
SEC = 2048
SEC_OFF, SEC_ADDR = 0x80, 0x00100000          # ELF 主段: 文件 0x80 <-> VA 0x100000

VA_HOOK = 0x21CC90
OLD_HOOK = 0x0062B823        # subu $s7, $v1, $v0     (wrapW = comp[0x40] - comp[0xB4])
NEW_HOOK = 0x0815966A        # j 0x005659A8

VA_CAVE = 0x5659A8
VTRSHTML = 0x005978C0        # __vt__6RSHTML (patch 时从 symtab 复核)
W_SF = 270                   # 特别收录介绍框宽度 (comp[0x40])

CAVE = [0x0062B823,          # subu  $s7, $v1, $v0   <- 原指令: 无条件先算原值
        0x3C080059,          # lui   $t0, 0x0059
        0x250878C0,          # addiu $t0, $t0, 0x78C0 ; t0 = 0x005978C0 (必须在比较前算完)
        0x8EA10000,          # lw    $at, 0($s5)      ; vptr
        0x14280007,          # bne   $at, $t0, +7     ; 非 RSHTML → 出口
        0x2401010E,          # addiu $at, $zero, 270  ; (延迟槽)
        0x14610005,          # bne   $v1, $at, +5     ; 宽 != 270 → 出口
        0x8EA20044,          # lw    $v0, 0x44($s5)   ; (延迟槽) v0 = H
        0x240100BE,          # addiu $at, $zero, 190  ; 190
        0x14410002,          # bne   $v0, $at, +2     ; 高 != 190 → 出口
        0x00000000,          # nop                    ; (延迟槽)
        0x3C177FFF,          # lui   $s7, 0x7FFF       ; ★ 命中 ⇒ wrapW = 0x7FFF0000
        0x08087325,          # j     0x0021CC94        ; 出口/回 DoWordWrap
        0x00000000]          # nop                    ; (j 的延迟槽, 本来就是 0)

CTX = [(0x21CC84, 0x8EA30040, 'lw   $v1, 0x40($s5)   ; comp[0x40] = W'),
       (0x21CC88, 0x92A200B4, 'lbu  $v0, 0xB4($s5)   ; comp[0xB4]'),
       (0x21CC94, 0x72E08E28, 'move $s1, $s7        ; 行预算 = wrapW (j 的延迟槽, 必须保留)')]

# 全 ELF 符号表 (与 tools/diag/dis_ee.py 同一口径)
STRTAB_OFF, STRTAB_LEN = 0x4DEDE0, 0x13E199
SYMTAB_OFF, SYMTAB_LEN = 0x61CF80, 0x97420


def file_off(va):
    return ELF_LBA * SEC + SEC_OFF + (va - SEC_ADDR)


def sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def diff_offsets(mm_a, path_b, chunk=1 << 22, cap=64):
    """mmap vs 文件: 逐块比较, 返回差异字节偏移 (最多 cap 个)。"""
    out, base = [], 0
    with open(path_b, 'rb') as fb:
        while True:
            x = mm_a[base:base + chunk]
            y = fb.read(chunk)
            if not x and not y:
                break
            if len(x) != len(y):
                return ['SIZE-MISMATCH']
            if x != y:
                xb, yb = bytes(x), y
                for i in range(len(xb)):
                    if xb[i] != yb[i]:
                        out.append(base + i)
                        if len(out) > cap:
                            return out
            base += chunk
    return out


def vt_from_symtab(src):
    """从源盘 ELF 的符号表里取 __vt__6RSHTML (只读, 用于复核常量)。"""
    with open(src, 'rb') as f:
        f.seek(ELF_LBA * SEC)
        head = f.read(SEC)
        assert head[:4] == b'\x7fELF', 'ELF_LBA 处不是 ELF'
        f.seek(ELF_LBA * SEC + STRTAB_OFF)
        strtab = f.read(STRTAB_LEN)
        f.seek(ELF_LBA * SEC + SYMTAB_OFF)
        sym = f.read(SYMTAB_LEN)
    for p in range(0, len(sym) - 16 + 1, 16):
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', sym, p)
        if not name:
            continue
        n = strtab[name:strtab.find(b'\0', name)].decode('latin-1')
        if n == '__vt__6RSHTML':
            return value
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--report', default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--allow-vt-mismatch', action='store_true',
                    help='符号表里 __vt__6RSHTML 与脚本常量不符时也继续 (默认拒绝)')
    a = ap.parse_args()

    src, dst = os.path.abspath(a.src), os.path.abspath(a.dst)
    assert os.path.isfile(src), src
    size = os.path.getsize(src)
    off_hook = file_off(VA_HOOK)
    off_cave = file_off(VA_CAVE)
    assert 0 <= off_hook < size and 0 <= off_cave + 4 * len(CAVE) < size, '落点越界'

    want_hook = OLD_HOOK if a.revert else NEW_HOOK
    other_hook = NEW_HOOK if a.revert else OLD_HOOK
    want_cave = [0] * len(CAVE) if a.revert else list(CAVE)

    report = dict(src=src, src_sha256=sha256(src), bytes=size,
                  hook_va='%08X' % VA_HOOK, hook_file_off=hex(off_hook),
                  old_hook='%08X' % OLD_HOOK, new_hook='%08X' % NEW_HOOK,
                  cave_va='%08X' % VA_CAVE, cave_words=len(CAVE),
                  cave_file_off=hex(off_cave),
                  condition='vptr==__vt__6RSHTML && comp[0x40]==%d' % W_SF,
                  direction='revert' if a.revert else 'apply')
    print('[site ] 挂点 VA %08X -> 文件偏移 0x%X' % (VA_HOOK, off_hook))
    print('       cave VA %08X -> 文件偏移 0x%X (%d 词)' % (VA_CAVE, off_cave, len(CAVE)))

    # ---- 类型常量复核 (从源盘符号表读, 不信任硬编码) ----
    vt = vt_from_symtab(src)
    report['vt_rshtml_symtab'] = '%08X' % vt if vt is not None else None
    print('[vt   ] 源盘符号表 __vt__6RSHTML = %s (脚本常量 %08X)'
          % ('%08X' % vt if vt is not None else '?', VTRSHTML))
    if vt is None:
        print('[warn ] 符号表里找不到 __vt__6RSHTML (也许被 strip); 按脚本常量继续')
    elif vt != VTRSHTML and not a.allow_vt_mismatch:
        print('[FAIL ] __vt__6RSHTML 漂移: 期望 %08X 实得 %08X —— 拒绝写盘' % (VTRSHTML, vt))
        print('         (若确认新值正确, 用 --allow-vt-mismatch 并同步更新脚本 CAVE[2]/CAVE[3])')
        return 3

    with open(src, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        cur_hook = struct.unpack_from('<I', mm, off_hook)[0]
        cur_cave = [struct.unpack_from('<I', mm, off_cave + 4 * i)[0] for i in range(len(CAVE))]
        print('       挂点原词 = %08X   目标词 = %08X' % (cur_hook, want_hook))
        print('       cave 原词 = %s' % ' '.join('%08X' % w for w in cur_cave))

        if cur_hook == want_hook and cur_cave == want_cave:
            print('[skip ] 挂点与 cave 都已是目标态 ⇒ 幂等, 不写任何字节')
            report['result'] = 'already'
        else:
            assert cur_hook == other_hook, \
                '挂点原词 %08X 既不是 %08X 也不是 %08X ⇒ 拒改' % (cur_hook, OLD_HOOK, NEW_HOOK)
            if not a.revert:
                for i, w in enumerate(cur_cave):
                    assert w == 0, 'cave 落点 @%08X 非零 (%08X) ⇒ 拒改' % (VA_CAVE + 4 * i, w)
            for va, w, txt in CTX:
                got = struct.unpack_from('<I', mm, file_off(va))[0]
                assert got == w, '上下文词不符 @%08X: %08X != %08X' % (va, got, w)
                print('       ctx %08X = %08X  (%s) ✓' % (va, got, txt))
            # 挂点不可被任何 j/jal/branch 直接进入 (只允许顺序落入)
            for va in (VA_HOOK, VA_HOOK + 4, VA_HOOK + 8):
                assert not branch_targets(mm, va), \
                    '%08X 有分支/跳转直接进入 ⇒ 拒改' % va
            report['result'] = 'patched'

        if not a.dry_run and report['result'] == 'already' and src != dst:
            shutil.copyfile(src, dst)
        if report['result'] == 'patched' and not a.dry_run:
            shutil.copyfile(src, dst)
            with open(dst, 'r+b') as f:
                f.seek(off_hook)
                f.write(struct.pack('<I', want_hook))
                for i, w in enumerate(want_cave):
                    if w or cur_cave[i]:
                        f.seek(off_cave + 4 * i)
                        f.write(struct.pack('<I', w))
                f.flush()
                os.fsync(f.fileno())
            # ---- 全盘回读比对 (白名单: 逐字节算出"真正会变的那些字节") ----
            expect = [off_hook + k for k in range(4)
                      if ((want_hook >> (8 * k)) & 0xFF) != ((cur_hook >> (8 * k)) & 0xFF)]
            for i in range(len(CAVE)):
                for k in range(4):
                    if ((want_cave[i] >> (8 * k)) & 0xFF) != ((cur_cave[i] >> (8 * k)) & 0xFF):
                        expect.append(off_cave + 4 * i + k)
            expect.sort()
            d = diff_offsets(mm, dst)
            print('[verify] 全盘差异 = %s' % ('恰好 %d B' % len(d) if len(d) <= 80
                                              else '%d 处' % len(d)))
            assert d == expect, ('差异窗口不符: 实得 %s\n  期望 %s'
                                 % ([hex(x) for x in d[:12]], [hex(x) for x in expect[:12]]))
            assert os.path.getsize(dst) == size
            with open(dst, 'rb') as f2:
                blob = f2.read(off_cave + 4 * len(CAVE))
                assert struct.unpack_from('<I', blob, off_hook)[0] == want_hook, '挂点回读不符'
                for i, w in enumerate(want_cave):
                    got = struct.unpack_from('<I', blob, off_cave + 4 * i)[0]
                    assert got == w, 'cave 第 %d 词回读不符 %08X != %08X' % (i, got, w)
            print('[write ] %s ✓  (大小不变, 全盘差异恰 %d B / 2 个窗口)' % (dst, len(d)))
            report['dst'] = dst
            report['dst_sha256'] = sha256(dst)
            report['diff_bytes'] = len(d)
            report['diff_window_hook'] = '[%s, %s]' % (hex(off_hook), hex(off_hook + 3))
            report['diff_window_cave'] = '[%s, %s]' % (hex(off_cave), hex(off_cave + 4 * len(CAVE) - 1))
        mm.close()
    report['mode'] = 'dry-run' if a.dry_run else 'write'
    if a.report:
        json.dump(report, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


def branch_targets(mm, va):
    """返回全 ELF 里以 va 为目标的 j/jal/branch 站点数 (只读扫描)。"""
    n = 0
    for off in range(0, 0x4DED00, 4):
        try:
            w = struct.unpack_from('<I', mm, ELF_LBA * SEC + SEC_OFF + off)[0]
        except Exception:                                       # noqa: BLE001
            break
        site = SEC_ADDR + off
        op = w >> 26
        if op in (2, 3):
            if ((w & 0x3FFFFFF) << 2) == va:
                n += 1
        elif op in (1, 4, 5, 6, 7):
            imm = w & 0xFFFF
            if imm >= 0x8000:
                imm -= 0x10000
            if site + 4 + (imm << 2) == va:
                n += 1
    return n


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
