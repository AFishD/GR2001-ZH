# -*- coding: utf-8 -*-
r"""patch_zh112_noautowrap.py — 关闭引擎自动折行: wrapW 设为"无穷大" (GR_ZH112)

## 用户需求 (原话)

> 发现折行有问题 能不能**取消引擎的自动折行 改为全部按照标签折行**

即: 引擎不再自己按宽度断行, 盘上文本里的 `{br}` / `{p}` (由 CSV 里的 `{WRAP}` /
"敲回车" 注入而来) 成为**唯一**的换行手段。

## wrapW 在哪里 (本轮逐字节核实, 见 docs/REPORT_noautowrap.md §1)

`wrapW` **不是**语言表里的字段, 也不是任何数据资源里的字段 —— 它是
`RSTextComponent::DoWordWrap @0x21CC10` 每次调用**当场算出来**的局部量:

    0x21CC84  lw   $v1, 0x40($s5)      ; $s5 = this = RSTextComponent*
    0x21CC88  lbu  $v0, 0xB4($s5)      ; (u8)
    0x21CC90  subu $s7, $v1, $v0       ; ★ $s7 = wrapW = comp[0x40] − comp[0xB4]
    0x21CC94  move $s1, $s7            ; 当前行剩余预算 = wrapW

(`comp[0x40]` = 该文本组件自己的宽度; 特别收录介绍框实测 = 270 ⇒ 这就是
`tools/text_csv` 里 `wrap_w=270` 那一列的来源 —— 工具侧的**标定常量**
`tcslib.WRAP_PROFILES['SFXML']`, 不是从盘上读出来的字段。)

## 本补丁 (1 个 ELF 词, 4 字节)

    0x21CC90  subu $s7, $v1, $v0   (0x0062B823)
      ->      lui  $s7, 0x7FFF     (0x3C177FFF)      ; wrapW = 0x7FFF0000 ≈ 2.1e9

语义: 每次进入 DoWordWrap 时 `wrapW` 直接取一个**任何一行都不可能达到**的值。于是:
  · 主干 token 循环里 `s1 (=wrapW) −= 宽度` 永不小于 0 ⇒ **永不记断点**;
  · 逐字硬断分支的门 `slt at, $s7, StringWidth(tok)` (0x21CD28) 永不成立 ⇒ **永不硬断**;
  · 函数尾部照旧把 `Length(text)` 压入断点数组 ⇒ RSHTML 已按 `{br}`/`{p}` 切好的
    **每个段恰好产生 1 行** ⇒ 全部换行只可能来自盘上的 `{br}`/`{p}`。

**为什么改这一处而不是改 `comp[0x40]`**: 组件宽度是 UI 布局量 (居中/滚动条/裁剪都用它),
动它会连带改布局; `wrapW` 只是"折行闸门", 改它不影响任何几何。也**不新建 cave** ——
`0x21CC90` 是 `subu` 的**单点**, 直接换词即可 (与 cave 方案相比零落点风险)。

## 回退

一个词换回 `0x0062B823` 即完全还原 (`--revert`, 或拿上一代盘重建)。
本补丁**只在 ISO 的 ELF 区原位覆写 4 字节**, 不改任何数据容器, 不改条目表,
不改文件大小。

## 硬断言 (写盘前 + 写盘后, 全部实测)

  ① 落点原词必须是 `0x0062B823`; 已是新词 ⇒ 幂等早退 (不写);
  ② 上下文词 0x21CC84 / 0x21CC88 / 0x21CC94 必须逐词相符 (证明改的是 DoWordWrap
     里那一处, 而不是同码异处);
  ③ 目标 VA 在主段内、4 字节对齐, 映射 `off = 295*2048 + 0x80 + (VA − 0x100000)`;
  ④ 写盘后**全盘逐块回读比对**: 差异必须恰好 4 字节且落在该落点 (白名单硬断言);
  ⑤ 产物大小 == 源盘大小 (1,648,164,864 B); `MENU.IMG` / `GR.IMG` 零触碰
     (由 ④ 的全盘比对直接保证)。

## 用法

    python tools/iso_build/patch_zh112_noautowrap.py <src.iso> <dst.iso> [--report <json>]
                                                    [--dry-run] [--revert]
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

VA = 0x21CC90
OLD = 0x0062B823        # subu $s7, $v1, $v0     (wrapW = comp[0x40] - comp[0xB4])
NEW = 0x3C177FFF        # lui  $s7, 0x7FFF       (wrapW = 0x7FFF0000, 实际无穷)

CTX = [(0x21CC84, 0x8EA30040, 'lw   v1, 0x40(s5)   ; comp[0x40]'),
       (0x21CC88, 0x92A200B4, 'lbu  v0, 0xB4(s5)   ; comp[0xB4]'),
       (0x21CC94, 0x72E08E28, 'move s1, s7        ; 行预算 = wrapW')]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--report', default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--revert', action='store_true')
    a = ap.parse_args()
    want = OLD if a.revert else NEW
    other = NEW if a.revert else OLD

    src, dst = os.path.abspath(a.src), os.path.abspath(a.dst)
    assert os.path.isfile(src), src
    size = os.path.getsize(src)
    off = file_off(VA)
    assert 0 <= off < size, '落点越界'

    with open(src, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        cur = struct.unpack_from('<I', mm, off)[0]
        print('[site ] VA %08X -> 文件偏移 0x%X' % (VA, off))
        print('       原词 = %08X   目标词 = %08X' % (cur, want))
        report = dict(src=src, src_sha256=sha256(src), bytes=size,
                      site='%08X' % VA, file_off=hex(off),
                      old_word='%08X' % OLD, new_word='%08X' % NEW,
                      direction='revert' if a.revert else 'apply')
        if cur == want:
            print('[skip ] 已是目标词 ⇒ 幂等, 不写任何字节')
            report['result'] = 'already'
        else:
            assert cur == other, '落点原词 %08X 既不是 %08X 也不是 %08X ⇒ 拒改' % (cur, OLD, NEW)
            for va, w, txt in CTX:
                got = struct.unpack_from('<I', mm, file_off(va))[0]
                assert got == w, '上下文词不符 @%08X: %08X != %08X' % (va, got, w)
                print('       ctx %08X = %08X  (%s) ✓' % (va, got, txt))
            report['result'] = 'patched'
        if not a.dry_run and report['result'] == 'already' and src != dst:
            shutil.copyfile(src, dst)
        if report['result'] == 'patched' and not a.dry_run:
            # ---- 写盘 (先整盘拷贝, 再原位覆写 4 字节) ----
            shutil.copyfile(src, dst)
            with open(dst, 'r+b') as f:
                f.seek(off)
                f.write(struct.pack('<I', want))
                f.flush()
                os.fsync(f.fileno())
            # ---- 全盘回读比对 (白名单: 恰好这 4 字节) ----
            d = diff_offsets(mm, dst)
            print('[verify] 全盘差异 = %s' % ([hex(x) for x in d] if len(d) <= 8 else '%d 处' % len(d)))
            assert d == [off, off + 1, off + 2, off + 3], '差异窗口不符'
            assert os.path.getsize(dst) == size
            with open(dst, 'rb') as f2:
                assert struct.unpack_from('<I', f2.read(off + 4), off)[0] == want, '回读不符'
            print('[write ] %s ✓  (大小不变, 全盘差异恰 4 B)' % dst)
            report['dst'] = dst
            report['dst_sha256'] = sha256(dst)
            report['diff_bytes'] = 4
            report['diff_offsets'] = [hex(x) for x in d]
        mm.close()
    report['mode'] = 'dry-run' if a.dry_run else 'write'
    if a.report:
        json.dump(report, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
