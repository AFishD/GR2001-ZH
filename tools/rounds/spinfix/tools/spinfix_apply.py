# -*- coding: utf-8 -*-
r"""spinfix_apply.py —— 【GR_SPINFIX】把分配器自旋修复（F1/F2/F4）打到成品盘上。

背景与站点（`docs\REPORT_USERDUMP_ANALYSIS.md` §6.2 定案，本工具不重查）
--------------------------------------------------------------------
卡死链：malloc(nb=0x10020) → 桶 126 的链头是越界坏值 → `0x1024D0 ld 8(v)` /
`0x102584 lw 0x14(v)` 反复 TLB Miss 读到 0 ⇒ **永不返回**（死在 malloc 内部）。
坏值是 free() 用不可信的 `prev_foot` 造出来的（`0x101DC0 subu $a1,$a1,$t2`），
再由大块插链 `0x102010/0x102014` 写进桶。

本工具实现三处：
  F1  0x00101DC0  `00AA2823 subu $a1,$a1,$t2` -> `j CAVE_F1`
      CAVE_F1：重算 P 并校验 `mstate < P < C` 且 `P%8==0`；不合法 -> `j 0x101DE4`
      （= 原有的「前块在用，不合并」出口，语义自洽：不合并只是少合并，不会野写）。
  F2  0x00101D38  `DCC90008 ld $t1,8($a2)` -> `j CAVE_F2`
      CAVE_F2：校验 `a2 = C+size` 满足 `C < a2 < 32MB`；不合法 -> `j 0x102018`
      （= free() 直接返回；放弃这次 free 只会泄漏一块，不会野写）。
  F4  0x00102588  `1459FFD1 bne $v0,$t9,-47` -> `j CAVE_F4`
      CAVE_F4：校验链头 `t9 < v0 < 0x1FFFFFFE`；不合法 -> `j 0x102590`
      （= 既有的「本桶没有可用块」出口，继续找下一个桶）。
  （F5 见文档：站点 0x101DC4/0x101DC8 只在 F1 的路径上，F1 已经校验过 P，
    单独出 F5 盘没有增量价值，故只在报告里给出编码与反汇编。）

★ 任务书给的 `sltiu $at,$v0,0x02000000` **无法编码**（SLTIU 立即数只有 16 位）；
  F4 改用 `sltu $at,$t9,$v0` + `sltu $t3,$v0,$t5`（t5 = 0x1FFFFFFE，malloc 自己
  在 0x1024BC 设好的 size 掩码）—— 上界放宽到 512 MB，但任何 ≥32 MB 的坏值
  （含用户的 0x6ED47823）仍被当场拦下；万一坏值落在 [32MB,512MB)，下一轮循环
  TLB Miss 后 v0 归 0，也会被 `t9 < v0` 拦下 ⇒ 仍不会自旋。

cave 落点（三处，全部经 spinfix_cave.py 审计 + probe_caves.py 在 8 份现场快照上
逐字节确认「运行期从未被写过」）：
  CAVE_F1 = 0x0055B730（68 B，零区 0x0055B730..0x0055B780 的前 68 B）
  CAVE_F2 = 0x005DECC4（44 B，零区 0x005DECC4..0x005DED00 的前 44 B）
  CAVE_F4 = 0x0041A35C（36 B，零区正好 36 B）
  避开：DBCS cave 全区 / 4 个闸门 / ZH cave block B / **GR_OOMFIX 已落地 cave
  0x00550048..0x00550080** / 分配器镜像 0x00101C00..0x00102700 / 解压器 0x00539110。

自证：尺寸不变 / 全盘 diff 只落在声明窗口 / 每个窗口都被写到 / 产物回读逐字相符 /
4 个闸门 + DBCS cave + ZH cave + OOMFIX cave + 另两个 cave 区 + ELF 头逐字节未动 /
自己的 cave 反汇编回读与设计一致。

只读基底；只写 --out / --meta。
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

SEC = 2048
ELF_NAME = C.ELF_NAME
ISO_OF_VA = C.ISO_OF_VA

BASES = {
    'lay1': dict(path=r'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso',
                 sha256='a69a9ca44049eaed4085239a2b8d10af58888f54f62a51e40c1ece22dd2d2808',
                 elf_sha256='0a986bb375176df41fad67798423f2e1a0a1c902d181ab9d673627a6d98387b9',
                 bytes=1648164864),
    '2400': dict(path=r'work\builds\GR_REBUILD\GR_REBUILD2400.iso',
                 sha256='d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0',
                 elf_sha256='5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8',
                 bytes=1648164864),
}

# ── 站点 ──────────────────────────────────────────────────────────────────────
F1 = dict(va=0x00101DC0, old=0x00AA2823, cave=0x0055B730, dis_old='subu $a1,$a1,$t2')
F2 = dict(va=0x00101D38, old=0xDCC90008, cave=0x005DECC4, dis_old='ld $t1,8($a2)')
F4 = dict(va=0x00102588, old=0x1459FFD1, cave=0x0041A35C, dis_old='bne $v0,$t9,-47')

# 必须逐字节不变的参照区（VA 区间）
REF_GATES = [0x00416EE8, 0x00417160, 0x0041751C, 0x005656A4]
REF_REGIONS = [
    (0x00416E00, 0x00417800, 'DBCS cave 全区'),
    (0x00565600, 0x00565B00, 'ZH cave block B'),
    (0x00550048, 0x00550080, '★GR_OOMFIX 已落地 cave'),
    (0x00539110, 0x00539310, '解压器本体（OOMFIX 线站点）'),
    (0x0051BE10, 0x0051C000, '解压器调用者'),
    (0x0021AC00, 0x0021AE00, 'RSFont 被替换函数区'),
    (0x00101D00, 0x00102700, '分配器镜像（只允许本盘声明的站点字）'),
]
REF_HEAD = (0, 0x1000)


def jword(target):
    assert target < 0x10000000
    return 0x08000000 | (target >> 2)


def cave_f1(base):
    skip = base + 0x3C
    valid = base + 0x34
    return [
        (0xDCA10000, 'ld $at,0($a1)          ; C->prev_foot'),
        (0x0001503C, 'dsll32 $t2,$at,0'),
        (0x000A503F, 'dsra32 $t2,$t2,0        ; t2 = (int32)prev_foot（与原代码一致）'),
        (0x00AA0823, 'subu $at,$a1,$t2        ; at = P = C - prev_size（原 subu 搬进 cave）'),
        (0x0081102B, 'sltu $v0,$a0,$at        ; v0 = (mstate < P)'),
        (0x0025682B, 'sltu $t5,$at,$a1        ; t5 = (P < C)'),
        (0x004D1024, 'and $v0,$v0,$t5         ; v0 = P 合法（严格在 (mstate, C) 内 ⇒ 必然在 RAM 内）'),
        (0x10400007, 'beq $v0,$zero,0x%08X    ; 不合法 -> .skip' % skip),
        (0x00000000, 'nop'),
        (0x30220007, 'andi $v0,$at,7          ; P % 8 == 0 ?'),
        (0x14400004, 'bne $v0,$zero,0x%08X    ; 未对齐 -> .skip' % skip),
        (0x00000000, 'nop'),
        (0x00202821, 'addu $a1,$at,$zero      ; a1 = P'),
        (jword(0x00101DC4), 'j 0x00101DC4            ; 回原流程：lw $t2,16(P) / 摘链 / 合并'),
        (0x00000000, 'nop'),
        (jword(0x00101DE4), 'j 0x00101DE4            ; .skip：跳过前块合并（= 原 PREV_INUSE 出口）'),
        (0x00000000, 'nop'),
    ]


def cave_f2(base):
    bad = base + 0x24
    return [
        (0x00A6102B, 'sltu $v0,$a1,$a2        ; v0 = (C < a2)'),
        (0x00060E42, 'srl $at,$a2,25          ; at = a2 >> 25（非 0 ⇔ a2 >= 32MB）'),
        (0x38420001, 'xori $v0,$v0,1          ; v0 = 1 ⇔ a2 <= C'),
        (0x00220825, 'or $at,$at,$v0          ; at != 0 ⇔ a2 不合法'),
        (0x14200004, 'bne $at,$zero,0x%08X    ; 不合法 -> .bad' % bad),
        (0x00000000, 'nop'),
        (0xDCC90008, 'ld $t1,8($a2)           ; 原 0x101D38'),
        (jword(0x00101D40), 'j 0x00101D40            ; 回原流程'),
        (0x00000000, 'nop'),
        (jword(0x00102018), 'j 0x00102018            ; .bad：放弃本次 free（只泄漏，不野写）'),
        (0x00000000, 'nop'),
    ]


def cave_f4(base):
    bad = base + 0x18
    return [
        (0x0322082B, 'sltu $at,$t9,$v0        ; at = (v0 > t9)（严格：排除 v0 == 桶哨兵）'),
        (0x004D582B, 'sltu $t3,$v0,$t5        ; t3 = (v0 < 0x1FFFFFFE)，t5 = malloc 在 0x1024BC 设的 0x1FFFFFFE'),
        (0x002B0824, 'and $at,$at,$t3         ; at != 0 ⇔ 链头看起来是 RAM 内的块'),
        (0x10200002, 'beq $at,$zero,0x%08X     ; 不合法 -> .bad' % bad),
        (0x00000000, 'nop'),
        (jword(0x001024D0), 'j 0x001024D0            ; 合法：回原循环体（= 原 bne 的回头路）'),
        (0x00000000, 'nop'),
        (jword(0x00102590), 'j 0x00102590            ; .bad：走既有的「本桶无可用块」出口'),
        (0x00000000, 'nop'),
    ]


FLAVORS = {
    'F4':      dict(sites=[F4],                  use_f1=False, use_f2=False),
    'F1F2':    dict(sites=[F1, F2],              use_f1=True,  use_f2=True),
    'F1F2_F4': dict(sites=[F1, F2, F4],          use_f1=True,  use_f2=True),
}

CAVES = {'F1': (F1, cave_f1), 'F2': (F2, cave_f2), 'F4': (F4, cave_f4)}


def build_cave(name):
    site, fn = CAVES[name]
    words = fn(site['cave'])
    return site, words, [w for (w, _d) in words]


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--flavor', required=True, choices=sorted(FLAVORS))
    ap.add_argument('--base-flavor', required=True, choices=sorted(BASES))
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--meta', default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    spec = BASES[a.base_flavor]
    base = os.path.abspath(os.path.join(C.ROOT, spec['path']))
    out = os.path.abspath(a.out)
    if base == out:
        raise SystemExit('--out 不能等于基底')
    tag = a.tag or os.path.splitext(os.path.basename(out))[0]

    base_sha = C.sha256_file(base)
    base_size = os.path.getsize(base)
    base_elf, lba, elf_size = C.read_elf_from_iso(base)
    base_elf_sha = hashlib.sha256(base_elf).hexdigest()
    ok_sha = (base_sha == spec['sha256'])
    ok_elf = (base_elf_sha == spec['elf_sha256'])
    if not a.force and not (ok_sha and ok_elf and base_size == spec['bytes']):
        raise SystemExit('[拒绝] 基底指纹不符：\n  iso %s（期望 %s）\n  elf %s（期望 %s）'
                         % (base_sha, spec['sha256'], base_elf_sha, spec['elf_sha256']))

    def bword(va):
        return C.word_at(base_elf, va, lba)

    fl = FLAVORS[a.flavor]
    plan = []
    for s in fl['sites']:
        name = {id(F1): 'F1', id(F2): 'F2', id(F4): 'F4'}[id(s)]
        got = bword(s['va'])
        assert got == s['old'], '%s 原字不符：%08X != %08X' % (name, got, s['old'])
        plan.append((name, s))

    # cave 词 + 零区断言
    cave_rep = []
    for name, s in plan:
        _, words, ws = build_cave(name)
        blob = base_elf[C.elf_off(s['cave'], lba):C.elf_off(s['cave'], lba) + 4 * len(ws)]
        assert set(blob) <= {0}, '%s cave 落点 0x%08X 不是全零！' % (name, s['cave'])
        cave_rep.append(dict(name=name, va='0x%08X' % s['cave'], words=['0x%08X' % w for w in ws],
                             iso_off='0x%08X' % (s['cave'] - ISO_OF_VA),
                             elf_off='0x%07X' % C.elf_off(s['cave'], lba),
                             bytes=4 * len(ws),
                             dis=C.dis_list(ws, s['cave'])))

    print('=' * 100)
    print('[spinfix] flavor=%s  base=%s' % (a.flavor, spec['path']))
    print('  基底 sha256=%s %s' % (base_sha, 'OK' if ok_sha else 'MISMATCH'))
    print('  ELF  @LBA %d %d B sha256=%s %s' % (lba, elf_size, base_elf_sha,
                                                'OK' if ok_elf else 'MISMATCH'))
    for name, s in plan:
        print('  %-4s 站点 0x%08X / ISO 0x%08X / ELF 0x%07X : %08X (%s) -> j 0x%08X'
              % (name, s['va'], s['va'] - ISO_OF_VA, C.elf_off(s['va'], lba),
                 s['old'], s['dis_old'], s['cave']))
    for c in cave_rep:
        print('  %-4s cave 0x%08X (%d B, 基底全零 ✓)  反汇编：' % (c['name'], int(c['va'], 16), c['bytes']))
        for line in c['dis']:
            print('        ' + line)

    # ── 写盘 ──────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        for name, s in plan:
            f.seek(s['va'] - ISO_OF_VA)
            f.write(struct.pack('<I', jword(s['cave'])))
        for c in cave_rep:
            f.seek(int(c['va'], 16) - ISO_OF_VA)
            for w in c['words']:
                f.write(struct.pack('<I', int(w, 16)))
        f.flush()
        os.fsync(f.fileno())

    # ── 回读 + 自证 ────────────────────────────────────────────────────────
    out_elf, lba2, size2 = C.read_elf_from_iso(out)

    def ord_(va):
        return C.word_at(out_elf, va, lba2)

    rb_sites = {name: ('0x%08X' % ord_(s['va'])) for name, s in plan}
    ok_sites = all(ord_(s['va']) == jword(s['cave']) for _n, s in plan)
    ok_caves = all(all(ord_(int(c['va'], 16) + 4 * i) == int(w, 16) for i, w in enumerate(c['words']))
                   for c in cave_rep)
    assert ok_sites and ok_caves, '回读不符'

    refs, ref_ok = [], True
    site_vas = {s['va'] for _n, s in plan}
    checks = [(0, 0x1000, 'ELF 头 + program headers')]
    for (lo, hi, why) in REF_REGIONS:
        checks.append((C.elf_off(lo, lba), C.elf_off(hi, lba), why))
    for (o0, o1, why) in checks:
        n = o1 - o0
        same = base_elf[o0:o0 + n] == out_elf[o0:o0 + n]
        if not same:
            b = bytearray(base_elf[o0:o0 + n])
            for va in site_vas:                      # 只放行本盘声明的站点字
                eo = C.elf_off(va, lba)
                if o0 <= eo < o1:
                    b[eo - o0:eo - o0 + 4] = struct.pack('<I', jword(
                        {F1['va']: F1['cave'], F2['va']: F2['cave'], F4['va']: F4['cave']}[va]))
            same = (bytes(b) == out_elf[o0:o0 + n])
        refs.append(dict(elf_off='0x%07X' % o0, elf_end='0x%07X' % o1, why=why, identical=bool(same)))
        ref_ok = ref_ok and same
    gates = ['0x%08X=0x%08X' % (g, ord_(g)) for g in REF_GATES]
    gates_ok = all(ord_(g) == bword(g) for g in REF_GATES)
    head_ok = (base_elf[0:0x1000] == out_elf[0:0x1000])
    assert gates_ok, '闸门被动了！'
    assert ref_ok, '参照区被动了！'

    runs = C.diff_runs(base, out)
    win = [(s['va'] - ISO_OF_VA, s['va'] - ISO_OF_VA + 4) for _n, s in plan] + \
          [(int(c['va'], 16) - ISO_OF_VA, int(c['va'], 16) - ISO_OF_VA + c['bytes']) for c in cave_rep]
    inwin = all(any(lo <= o and o + len(ob) <= hi for (lo, hi) in win) for (o, ob, _n) in runs)
    nb = sum(len(ob) for (_o, ob, _n) in runs)
    touched = sum(1 for (lo, hi) in win if any(lo <= o < hi for (o, _ob, _n) in runs))
    out_sha = C.sha256_file(out)
    out_size = os.path.getsize(out)

    rep = dict(tag=tag, flavor=a.flavor, base_flavor=a.base_flavor,
               tool=r'work\builds\GR_SPINFIX\tools\spinfix_apply.py',
               base_file=base, base_sha256=base_sha, base_bytes=base_size,
               base_elf_sha256=base_elf_sha, base_elf_lba=lba, base_elf_bytes=elf_size,
               sites=[dict(name=n, va='0x%08X' % s['va'], iso_off='0x%08X' % (s['va'] - ISO_OF_VA),
                           elf_off='0x%07X' % C.elf_off(s['va'], lba),
                           old_word='0x%08X' % s['old'], old_dis=s['dis_old'],
                           new_word='0x%08X' % jword(s['cave']), new_dis='j 0x%08X' % s['cave'],
                           delay_slot=dict(va='0x%08X' % (s['va'] + 4),
                                           word='0x%08X' % bword(s['va'] + 4),
                                           note='未改，语义见报告'))
                      for n, s in plan],
               caves=cave_rep,
               ref_regions=refs, gates_readback=gates,
               elf_header_identical=bool(head_ok),
               out=os.path.relpath(out, C.ROOT), out_file=os.path.basename(out),
               bytes=out_size, sha256=out_sha,
               out_elf_sha256=hashlib.sha256(out_elf).hexdigest(),
               diff_runs=[dict(iso_off='0x%08X' % o, len=len(ob), old=ob.hex(), new=nb2.hex())
                          for (o, ob, nb2) in runs],
               diff_run_count=len(runs), diff_bytes=nb,
               selfcheck=dict(size_unchanged=(out_size == base_size),
                              diff_only_in_declared_windows=bool(inwin),
                              every_window_touched=(touched == len(win)),
                              readback_all_ok=bool(ok_sites and ok_caves),
                              gates_untouched_4=bool(gates_ok),
                              dbcs_zh_oomfix_caves_untouched=bool(
                                  all(r['identical'] for r in refs
                                      if 'cave' in r['why'] or 'RSFont' in r['why'])),
                              elf_header_untouched=bool(head_ok),
                              elf_lba_size_unchanged=(lba2 == lba and size2 == elf_size)))
    print('\n[写出] %s  (%d B, sha256=%s)' % (out, out_size, out_sha))
    print('  ELF sha256 = %s' % rep['out_elf_sha256'])
    print('  diff = %d run / %d B' % (len(runs), nb))
    for r in runs:
        print('    0x%08X +%-3d %s -> %s' % (r[0], len(r[1]), r[1].hex(), r[2].hex()))
    for k, v in rep['selfcheck'].items():
        print('  自证 %-40s %s' % (k, 'OK' if v else 'FAIL'))
    print('  闸门回读 %s' % ' / '.join(gates))
    mp = a.meta or (os.path.splitext(out)[0] + '.meta.json')
    with open(mp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('[meta] %s' % mp)
    return 0 if (inwin and ok_sites and ok_caves and gates_ok and ref_ok
                 and out_size == base_size and touched == len(win)) else 1


if __name__ == '__main__':
    sys.exit(main())
