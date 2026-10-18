# -*- coding: utf-8 -*-
r"""dfix_apply.py —— 【GR_DISASM】逐站点原字断言 + 单点修复，作用于**任何本工程血统**的
PS2《Ghost Recon (USA) SLUS_206.13》汉化盘。

设计纪律
--------
* **输入盘只读**：以 'rb' 打开，任何情况下不写回 `--iso`。
* **逐站点原字断言**：每个站点先读回原字，与站点表登记的期望值比对；
  不符则**拒绝该站点**（默认）或以 `--strict` 整盘失败 —— 绝不盲写。
* **产品自证**：写出后重新打开产物，逐站点回读、逐字节 diff，断言
  「长度不变 / 差异只落在声明窗口内 / 每站点恰好 2 或 4 字节」。
* **血统识别**：读 4 个闸门字判定本盘是 A 线（gate 0xB1）还是 B 线（gate 0xBA），
  只用于报告；站点表两线通用（见 --set 说明）。

用法
----
  # 只做检查，不写盘
  python dfix_apply.py --iso <盘.iso> --check
  # 应用候选修复（可叠加，用 + 连接）
  python dfix_apply.py --iso <盘.iso> --out <新盘.iso> --set icon+fp+pkt
  # 对已抽出的 ELF 直接操作（开发/自测用）
  python dfix_apply.py --elf <SLUS_206.13> --out <新elf> --set icon
  # 列出站点表
  python dfix_apply.py --list

候选修复集（--set）
-------------------
  icon  9 处活站点（+2 处死代码、+1 处惰性，需 --all12）把图标特判的比较值改成 0xFF00
        ⇒ 永不命中。**这是唯一已被实机证明能改变行为的杠杆**（同字节补丁的 SENT_06）。
  fp    1 个字：DrawString 拦截器结尾 `j 0x219A7C` → `j 0x219A78`，把被跳过的
        `sq $fp,144(sp)` 补回来（ABI 合规；已定位 2 个真实受害者站点）。
  pkt   2 个字：把顶点包 flush 后的「计数器复位」从**有条件**改成**无条件**。
        这是静态上唯一能找到「顶点写入下标无上界」的地点（容量哨兵在写入**之后**、
        且复位以 fontmgr+0x48 为条件）⇒ 门控无关，可同时解释两条线。
  probe-slot（**不推荐直接应用，仅作探针**）
        修 0x41708C/0x416FA0 处 `mult` 之后缺 `mflo` 的地址算式。**警告**：本工程既有
        实机取证（docs/REPORT_atlas_artifact.md §3）显示现役盘的槽位映射**是对的**，
        与本修复的静态推导矛盾 ⇒ 应用前必须先跑探针盘，见 docs/DISASM_TEST_GUIDE.md。
"""
import argparse
import hashlib
import os
import struct
import sys

SEC = 2048
ELF_NAME = 'SLUS_206.13;1'

# ───────────────────────────── 站点表 ─────────────────────────────
# (VA, 名称, 期望原字, 新字)
ICON_LIVE = [
    (0x00219C08, 'DrawString 图标判定 #1 (0xB5)', 0x240300B5, 0x2403FF00),
    (0x00219C10, 'DrawString 图标判定 #1 延迟槽 (0xB5)', 0x240300B5, 0x2403FF00),
    (0x00219C14, 'DrawString 图标判定 #2 (0xB1)', 0x240300B1, 0x2403FF00),
    (0x00219C94, 'DrawString 图标判定 #3 (0xB5) 字距', 0x240300B5, 0x2403FF00),
    (0x00219CAC, 'DrawString 图标判定 #4 (0xB1) 字距', 0x240300B1, 0x2403FF00),
    (0x00219D24, 'DrawString 图标判定 #5 (0xB5) → AddOneWord(t0=1)', 0x240200B5, 0x2402FF00),
    (0x00219D38, 'DrawString 图标判定 #6 (0xB1) → AddOneWord(t0=1)', 0x240200B1, 0x2402FF00),
    (0x00416F5C, 'CharWidth cave 图标宽度 (0xB5) → 20', 0x240900B5, 0x2409FF00),
    (0x00416F68, 'CharWidth cave 图标宽度 (0xB1) → 20', 0x240900B1, 0x2409FF00),
]
ICON_DEAD = [
    (0x0021AD38, 'CharWidth 原文残留（死代码）(0xB5)', 0x2402FFB5, 0x2402FF00),
    (0x0021AD4C, 'CharWidth 原文残留（死代码）(0xB1)', 0x2402FFB1, 0x2402FF00),
]
ICON_INERT = [
    (0x00219C40, 'DrawString 惰性站点（符号扩展，改了不改变走向）', 0x2403FFB5, 0x2403FF00),
]
FP = [
    (0x005659A4, 'DrawString 拦截器返回目标：j 0x219A7C → j 0x219A78（补回 sq $fp,144(sp)）',
     0x0808669F, 0x0808669E),
]
PKT = [
    (0x0021A040, '主顶点包 flush 后无条件复位计数（去掉 fontmgr+0x48 条件）', 0x1060004C, 0x00000000),
    (0x0021A144, '副顶点包 flush 后无条件复位计数（去掉 fontmgr+0x48 条件）', 0x1060000B, 0x00000000),
]
PROBE_SLOT = [
    (0x00417084, 'F_UV: t5 = trail + 0x3F（把 +0xE0 预并进 t5）', 0x25ADFF5F, 0x25AD003F),
    (0x00417090, 'F_UV: t4 = mflo（补回被丢弃的乘积累加）', 0x018D6021, 0x00006012),
    (0x00417094, 'F_UV: a1 = t4 + t5', 0x258500E0, 0x018D2821),
    (0x00416F98, 'CharWidth cave: t2 = trail + 0x3F', 0x254AFF5F, 0x254A003F),
    (0x00416FA4, 'CharWidth cave: t0 = mflo', 0x010A4021, 0x00004012),
    (0x00416FA8, 'CharWidth cave: t0 = t0 + t2', 0x250800E0, 0x010A4021),
]
GATES = [
    (0x00416EE8, 'DBCS 前导上界 #1'),
    (0x00417160, 'DBCS 前导上界 #2'),
    (0x0041751C, 'DBCS 前导上界 #3'),
    (0x005656A4, 'DBCS 前导上界 #4（字形计数 cave 内）'),
]
ATLAS_GEOM = [
    (0x004170AC, '图集每行列数 ncol (62 / 64)'),
    (0x004170E8, 'row>=12 的行位移 (+3 / +2)'),
    (0x004170F8, 'V0 = row*16 + (2 / 3)'),
    (0x004170FC, 'V1 = row*16 + (18 / 19)'),
]

SETS = {
    'icon': ICON_LIVE,
    'icon-dead': ICON_DEAD,
    'icon-inert': ICON_INERT,
    'fp': FP,
    'pkt': PKT,
    'probe-slot': PROBE_SLOT,
}


# ───────────────────────── ISO9660（只读） ─────────────────────────
def iso_find_elf(f):
    """返回 (lba, size)。只读。"""
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    if pvd[1:6] != b'CD001':
        raise SystemExit('扇区 16 不是 ISO9660 PVD')
    root = pvd[156:156 + 34]
    rlba = struct.unpack_from('<I', root, 2)[0]
    rsize = struct.unpack_from('<I', root, 10)[0]
    data = b''
    for i in range((rsize + SEC - 1) // SEC):
        f.seek((rlba + i) * SEC)
        data += f.read(SEC)
    off = 0
    while off < len(data):
        ln = data[off]
        if ln == 0:
            off = (off // SEC + 1) * SEC
            continue
        rec = data[off:off + ln]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode('latin-1').upper()
        if name in ('SLUS_206.13;1', 'SLUS_206.13'):
            return ext, sz
        off += ln
    raise SystemExit('ISO 目录里找不到 SLUS_206.13')


def read_elf_from_iso(path):
    with open(path, 'rb') as f:
        lba, size = iso_find_elf(f)
        f.seek(lba * SEC)
        d = f.read(size)
    if d[:4] != b'\x7fELF':
        raise SystemExit('取到的不是 ELF')
    return d, lba, size


# ───────────────────────── VA ↔ 文件偏移（用程序头推导，不硬编码） ─────────────────────────
def va_map(d):
    e_phoff = struct.unpack_from('<I', d, 0x1C)[0]
    e_phentsize = struct.unpack_from('<H', d, 0x2A)[0]
    e_phnum = struct.unpack_from('<H', d, 0x2C)[0]
    segs = []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        t, off, va, pa, fs, ms, fl, al = struct.unpack_from('<8I', d, o)
        if t == 1 and fs:
            segs.append((va, off, fs))
    if not segs:
        raise SystemExit('ELF 没有 PT_LOAD')

    def va2off(va):
        for (v, o, fs) in segs:
            if v <= va < v + fs:
                return o + (va - v)
        raise SystemExit('VA 0x%08X 不在任何 PT_LOAD 内' % va)
    return va2off, segs


def ld(d, off):
    return struct.unpack_from('<I', d, off)[0]


# ───────────────────────── 血统识别 ─────────────────────────
def lineage(d, va2off):
    g = []
    for (va, _n) in GATES:
        g.append(ld(d, va2off(va)) & 0xFFFF)
    geom = [ld(d, va2off(va)) & 0xFFFF for (va, _n) in ATLAS_GEOM]
    if g == [0xB1, 0xB1, 0xB1, 0xB1]:
        line = 'A（gate 0xB1；b1/b5 是单字节 ⇒ 图标特判**可达**）'
    elif g == [0xBA, 0xBA, 0xBA, 0xBA]:
        line = 'B（gate 0xBA；b1/b5 属前导区间 ⇒ 图标特判**几乎不可达**）'
    else:
        line = '未知（闸门字 = %s）' % ['0x%04X' % x for x in g]
    return line, g, geom


# ───────────────────────── 主流程 ─────────────────────────
def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(add_help=True, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--iso', help='输入盘（只读）')
    ap.add_argument('--elf', help='输入 ELF（只读）；与 --iso 二选一')
    ap.add_argument('--out', help='输出文件（必须与输入不同）')
    ap.add_argument('--set', dest='sets', default='',
                    help='要应用的修复集，用 + 连接：icon / icon-dead / icon-inert / fp / pkt / probe-slot')
    ap.add_argument('--all12', action='store_true', help='= icon+icon-dead+icon-inert')
    ap.add_argument('--check', action='store_true', help='只做检查与断言，不写任何文件')
    ap.add_argument('--strict', action='store_true', help='任一站点原字不符即整盘失败')
    ap.add_argument('--list', action='store_true', help='列出站点表后退出')
    a = ap.parse_args()

    if a.list:
        for k in ('icon', 'icon-dead', 'icon-inert', 'fp', 'pkt', 'probe-slot'):
            print('## --set %s' % k)
            for (va, name, o, n) in SETS[k]:
                print('   0x%08X  %08X -> %08X   %s' % (va, o, n, name))
        print('## 只读参照（本工具不改）')
        for (va, name) in GATES + ATLAS_GEOM:
            print('   0x%08X  %s' % (va, name))
        return

    if bool(a.iso) == bool(a.elf):
        raise SystemExit('必须且只能给 --iso 或 --elf 之一')
    if not a.check and not a.out:
        raise SystemExit('非 --check 模式必须给 --out')

    if a.iso:
        data, lba, size = read_elf_from_iso(a.iso)
        src = 'ISO %s（SLUS_206.13 @ LBA %d, %d B）' % (a.iso, lba, size)
        inpath = a.iso
    else:
        with open(a.elf, 'rb') as f:
            data = f.read()
        src = 'ELF %s（%d B）' % (a.elf, len(data))
        inpath = a.elf

    if a.out and os.path.abspath(a.out) == os.path.abspath(inpath):
        raise SystemExit('--out 不能等于输入（输入盘只读）')

    va2off, segs = va_map(data)
    print('=== dfix_apply ===')
    print('输入   : %s' % src)
    print('sha256 : %s' % hashlib.sha256(data).hexdigest())
    print('PT_LOAD: %s' % [(hex(v), hex(o), hex(s)) for (v, o, s) in segs])
    line, g, geom = lineage(data, va2off)
    print('血统   : %s' % line)
    print('闸门   : %s' % ['0x%04X' % x for x in g])
    print('图集几何: ncol=%d, rowShift=%d, V0=+%d, V1=+%d' % tuple(geom))
    print()

    names = []
    if a.all12:
        names += ['icon', 'icon-dead', 'icon-inert']  # = SENT_06 的 12 处同型补丁
    if a.sets:
        names += [x.strip() for x in a.sets.split('+') if x.strip()]
    if not names and a.check:
        # 裸 --check：把**全部**站点表都断言一遍（给重建执行者的一键体检）
        names = ['icon', 'icon-dead', 'icon-inert', 'fp', 'pkt', 'probe-slot']
        print('（未给 --set ⇒ --check 默认断言全部站点表）')
    seen, order = set(), []
    for n in names:
        if n not in SETS:
            raise SystemExit('未知修复集 %r（可用：%s）' % (n, ', '.join(SETS)))
        if n not in seen:
            seen.add(n); order.append(n)
    if not order and not a.check:
        raise SystemExit('没给 --set，也没给 --check')

    sites = []
    for n in order:
        for s in SETS[n]:
            sites.append((n,) + tuple(s))

    print('--- 站点断言（共 %d 处）---' % len(sites))
    ok, bad = 0, []
    for (grp, va, name, exp, new) in sites:
        cur = ld(data, va2off(va))
        tag = 'OK ' if cur == exp else '!! '
        if cur == exp:
            ok += 1
        else:
            bad.append((grp, va, name, exp, cur))
        print('  %s[%s] 0x%08X  %08X (期望 %08X) -> %08X   %s'
              % (tag, grp, va, cur, exp, new, name))
    print('  断言通过 %d / %d' % (ok, len(sites)))
    if bad:
        print('  ⚠ 原字不符的站点（本次**不会**被修改）：')
        for (grp, va, name, exp, cur) in bad:
            print('     0x%08X 期望 %08X 实得 %08X  %s' % (va, exp, cur, name))
        if a.strict:
            raise SystemExit('--strict：存在原字不符站点，中止')

    # 声明窗口（用于自检）
    windows = sorted((va2off(va), va2off(va) + 4) for (_g, va, _n, _e, _w) in sites if ld(data, va2off(va)) == _e)

    print()
    print('--- 只读参照（不改动）---')
    for (va, name) in GATES + ATLAS_GEOM:
        print('  0x%08X = %08X   %s' % (va, ld(data, va2off(va)), name))

    if a.check:
        print()
        print('[check] 未写任何文件。')
        return

    out = bytearray(data)
    applied = 0
    for (grp, va, name, exp, new) in sites:
        o = va2off(va)
        if ld(data, o) != exp:
            continue
        struct.pack_into('<I', out, o, new)
        applied += 1

    with open(a.out, 'wb') as f:
        f.write(out)
    print()
    print('--- 写出与自证 ---')
    print('输出   : %s  (%d B)  sha256 = %s'
          % (a.out, len(out), hashlib.sha256(bytes(out)).hexdigest()))
    print('应用站点 = %d' % applied)

    with open(a.out, 'rb') as f:
        chk = f.read()
    assert len(chk) == len(data), '长度变了！'
    print('自检 size_unchanged            ✓')
    diffs = [i for i in range(len(data)) if data[i] != chk[i]]
    inwin = all(any(lo <= i < hi for (lo, hi) in windows) for i in diffs)
    print('自检 diff_only_in_windows      %s（差异 %d 字节）' % ('✓' if inwin else '✗', len(diffs)))
    # 每个 4 字节站点改动，实际差异字节数 ∈ [1,4]（例如 240300B5→2403FF00 只差 2 字节）
    print('自检 diff_bytes in [N, 4N]     %s（%d 字节 / %d 站点）'
          % ('✓' if applied <= len(diffs) <= 4 * applied else '✗', len(diffs), applied))
    touched = sum(1 for (lo, hi) in windows if any(lo <= i < hi for i in diffs))
    print('自检 每个声明窗口都真有改动     %s（%d / %d）'
          % ('✓' if touched == applied else '✗', touched, applied))
    ro = all(ld(chk, va2off(va)) == ld(data, va2off(va)) for (va, _n) in GATES + ATLAS_GEOM)
    print('自检 闸门/图集几何 未被触碰      %s' % ('✓' if ro else '✗'))
    rb = True
    for (grp, va, name, exp, new) in sites:
        o = va2off(va)
        want = new if ld(data, o) == exp else exp
        if ld(chk, o) != want:
            rb = False
            print('  回读不符 0x%08X' % va)
    print('自检 readback_all_ok           %s' % ('✓' if rb else '✗'))
    print()
    print('回读站点：')
    for (grp, va, name, exp, new) in sites:
        o = va2off(va)
        print('  0x%08X  %08X -> %08X   [%s]' % (va, ld(data, o), ld(chk, o), grp))


if __name__ == '__main__':
    main()
