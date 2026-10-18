# -*- coding: utf-8 -*-
r"""combfix_apply.py —— 【GR_COMBFIX】组合修复盘出盘工具（SPINFIX_F4 + OOMFIX + F1/F1b/F7）。

背景
----
* 基底 A/B/C = `work\builds\GR_SPINFIX\SPINFIX_F4.iso`（已含 F4：站点 0x102588 + cave 0x41A35C）
  基底 2400   = `work\builds\GR_REBUILD\GR_REBUILD2400.iso`（未打任何补丁 ⇒ 本工具自己打 F4）
* 本轮新病灶（`docs\REPORT_COMBFIX.md` §A）：malloc 的「请自己的桶」快路径
  `0x10216C lw v0,4(v0)` → `0x102180 ld v1,8(v0)` → `0x1021D0 lw v0,20(v0)`
  → `0x1021D4 bne v0,a3,-22` 这条**回边没有校验**，桶 126 的坏链头（0xF968B859，
  未映射 KUSEG/KSEG2）被读成 0 之后 `v0 != a3` 永远成立 ⇒ 死循环。
  F4 只挂了 binmap 扫描的回边 `0x102588`，覆盖不到它。

本工具的补丁
------------
OOMFIX  0x00539174 `AE620004 sw $v0,4($s3)` -> `j 0x00550048`；cave 0x00550048（44 B，11 字）
        = GR_OOMFIX 原样（含 s0 置 0 让调用者失败分支生效）。
F1      0x00101DC0 `00AA2823 subu $a1,$a1,$t2` -> `j 0x0055B730`；cave 0x0055B730（68 B，17 字）
        = SPINFIX 原样（逐字节相同，位置相同）。
F1b     0x00101D60 `00A42823 subu $a1,$a1,$a0` -> `j 0x005DECC4`；cave 0x005DECC4（56 B，14 字）
        = 本工程新写：`next == top` 支的同族病灶（SPINFIX §4.3 残余风险①）。
        ★ 与 SPINFIX §4.3 的「同一个 cave 体」不同：站点 0x101D60 的**延迟槽**
          `0x101D64 daddu $v1,$v1,$a2` 会先执行，所以（a）合法出口必须是 0x101D68
          而不是 0x101D64；（b）不合法出口必须在 cave 里 `dsubu $v1,$v1,$a2` 把
          prev_foot 撤销，否则 0x101D94 `sd $v1,8($a1)` 会把垃圾尺寸写进 C 的 head。
          详见 REPORT_COMBFIX §B/§C 的指令级说明。
F7      0x001021D4 `1447FFEA bne $v0,$a3,-22` -> `j 0x005DECC4`；cave 0x005DECC4（36 B，9 字）
        = 本工程新写：own-bin 回边校验 `a3 < v0 < a2(=0x1FFFFFFE)`；不合法 ->
          `j 0x001021E0`（既有的「本桶无可用块、换下一个桶」出口）。

cave 落点（全部经 combfix_cave.py / combfix_cave2.py 审计）：
  R1 0x0055B730..0x0055B780（80 B，SPINFIX 已用前 68 B）——F1
  R2 0x005DECC4..0x005DED00（60 B，SPINFIX F2 曾用前 44 B）——F1b（56 B）/ F7（36 B）
  R3 0x0041A35C（36 B）——F4（继承 SPINFIX）
  R4 0x00550048..0x00550080（56 B）——OOMFIX（44 B）
避开：DBCS cave 全区 0x416E00..0x417800、4 个闸门、ZH cave block B 0x565600..0x565B00、
      分配器镜像 0x101C00..0x102700、解压器 0x539110..0x539310、RSFont 0x21AC00..0x21AE00。

自证 8 项：尺寸不变 / diff 只落在声明窗口 / 每个窗口都被写到 / 回读逐字相符 /
4 闸门未动 / DBCS+ZH+别的工程 cave 未动 / ELF 头未动 / ELF LBA 与大小不变。

只读基底；只写 --out / --meta。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import sys

ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO_OF_VA = 0x6C780
ELF_LBA = 295
SEC = 2048
ELF_NAME = 'SLUS_206.13'

BASES = {
    'layA': dict(path=r'work\builds\GR_SPINFIX\SPINFIX_F4.iso',
                 sha256='9704600e5118c2b3bf217b8414fcd8682a2f5b72d875c80029dbdcaee1af34e2',
                 elf_sha256='fb60afc4', bytes=1648164864,
                 has_f4=True, note='SPINFIX_F4.iso（LAY_fix1_bytecount + F4）'),
    '2400': dict(path=r'work\builds\GR_REBUILD\GR_REBUILD2400.iso',
                 sha256='d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0',
                 elf_sha256='5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8',
                 bytes=1648164864,
                 has_f4=False, note='GR_REBUILD2400.iso（产品线，未打任何补丁）'),
}

# ── 站点 ──────────────────────────────────────────────────────────────────────
OOMFIX = dict(name='OOMFIX', va=0x00539174, old=0xAE620004,
              dis_old='sw $v0,4($s3)', cave=0x00550048,
              resume_dis='j 0x0053917C（延迟槽 0x539178 原指令照跑）')
F4 = dict(name='F4', va=0x00102588, old=0x1459FFD1,
          dis_old='bne $v0,$t9,-47', cave=0x0041A35C, resume_dis='j 0x001024D0 / bail j 0x00102590')
F1 = dict(name='F1', va=0x00101DC0, old=0x00AA2823,
          dis_old='subu $a1,$a1,$t2', cave=0x0055B730, resume_dis='j 0x00101DC4 / bail j 0x00101DE4')
F1b = dict(name='F1b', va=0x00101D60, old=0x00A42823,
           dis_old='subu $a1,$a1,$a0', cave=0x005DECC4,
           resume_dis='j 0x00101D68（0x101D64 已由延迟槽执行）/ bail j 0x00101D78（先 dsubu v1,v1,a2）')
F7 = dict(name='F7', va=0x001021D4, old=0x1447FFEA,
          dis_old='bne $v0,$a3,-22', cave=0x005DECC4,
          resume_dis='j 0x00102180（回本桶扫描循环体）/ bail j 0x001021E0（换下一个桶）')


def jword(t):
    assert t < 0x10000000
    return 0x08000000 | (t >> 2)


def cave_oomfix(base):
    fail = base + 0x18
    return [
        (0x10400005, 'beq $v0,$zero,0x%08X    ; malloc 返回 0 ?' % fail),
        (0x00000000, 'nop'),
        (0xAE620004, 'sw $v0,4($s3)          ; 成功：输出缓冲基址'),
        (0xAE620008, 'sw $v0,8($s3)          ; 成功：输出游标'),
        (jword(0x0053917C), 'j 0x0053917C            ; 回原流程'),
        (0x00000000, 'nop'),
        (0xAE600004, 'sw $zero,4($s3)        ; .fail：基址 = 0'),
        (0xAE600008, 'sw $zero,8($s3)        ; .fail：游标 = 0'),
        (0x0000802D, 'daddu $s0,$zero,$zero ; ★ s0 = 0 ⇒ 返回 0'),
        (jword(0x005392A0), 'j 0x005392A0            ; 走既有尾声'),
        (0x00000000, 'nop'),
    ]


def cave_f1(base):
    skip = base + 0x3C
    return [
        (0xDCA10000, 'ld $at,0($a1)          ; C->prev_foot'),
        (0x0001503C, 'dsll32 $t2,$at,0'),
        (0x000A503F, 'dsra32 $t2,$t2,0        ; t2 = (int32)prev_foot'),
        (0x00AA0823, 'subu $at,$a1,$t2        ; at = P'),
        (0x0081102B, 'sltu $v0,$a0,$at        ; mstate < P'),
        (0x0025682B, 'sltu $t5,$at,$a1        ; P < C'),
        (0x004D1024, 'and $v0,$v0,$t5'),
        (0x10400007, 'beq $v0,$zero,0x%08X    ; 不合法 -> .skip' % skip),
        (0x00000000, 'nop'),
        (0x30220007, 'andi $v0,$at,7          ; P % 8 == 0 ?'),
        (0x14400004, 'bne $v0,$zero,0x%08X    ; 未对齐 -> .skip' % skip),
        (0x00000000, 'nop'),
        (0x00202821, 'addu $a1,$at,$zero      ; a1 = P'),
        (jword(0x00101DC4), 'j 0x00101DC4            ; 回原流程（延迟槽已跑过 0x101DC4）'),
        (0x00000000, 'nop'),
        (jword(0x00101DE4), 'j 0x00101DE4            ; .skip：不合并前块（= 原 PREV_INUSE 出口）'),
        (0x00000000, 'nop'),
    ]


def cave_f1b(base):
    bail = base + 0x30
    return [
        (0x00A40823, 'subu $at,$a1,$a0        ; at = P = C - (int32)prev_foot（原 0x101D60 搬进 cave）'),
        (0x25020008, 'addiu $v0,$t0,8         ; v0 = mstate（t0 = mstate-8，在 0x101D20 设定）'),
        (0x0041102B, 'sltu $v0,$v0,$at        ; mstate < P'),
        (0x0025682B, 'sltu $t5,$at,$a1        ; P < C'),
        (0x004D1024, 'and $v0,$v0,$t5'),
        (0x10400006, 'beq $v0,$zero,0x%08X    ; 不合法 -> .bail' % bail),
        (0x30220007, 'andi $v0,$at,7          ; 延迟槽：P % 8 == 0 ?'),
        (0x14400004, 'bne $v0,$zero,0x%08X    ; 未对齐 -> .bail' % bail),
        (0x00000000, 'nop                     ; 延迟槽：不动 $a1'),
        (0x00202821, 'addu $a1,$at,$zero      ; a1 = P'),
        (jword(0x00101D68), 'j 0x00101D68            ; 回原流程（0x101D64 已由本站点延迟槽执行）'),
        (0x00000000, 'nop'),
        (0x00A6182F, 'dsubu $v1,$v1,$a2       ; ★ 撤销延迟槽 0x101D64 加进来的 prev_foot'),
        (jword(0x00101D78), 'j 0x00101D78            ; .bail：跳过前块合并（a1 仍为 C）'),
    ]


def cave_f7(base):
    bail = base + 0x1C
    return [
        (0x00E2082B, 'sltu $at,$a3,$v0        ; v0 > 桶哨兵 a3（严格）'),
        (0x0046182B, 'sltu $v1,$v0,$a2        ; v0 < 0x1FFFFFFE（a2 在 0x10217C 设的掩码）'),
        (0x00230824, 'and $at,$at,$v1'),
        (0x10200003, 'beq $at,$zero,0x%08X    ; 不像 RAM 内的块 -> .bail' % bail),
        (0x00000000, 'nop'),
        (jword(0x00102180), 'j 0x00102180            ; 合法 -> 回本桶扫描循环体'),
        (0x00000000, 'nop'),
        (jword(0x001021E0), 'j 0x001021E0            ; .bail -> 既有的「换下一个桶」出口'),
        (0x00000000, 'nop'),
    ]


def cave_f4(base):
    bad = base + 0x18
    return [
        (0x0322082B, 'sltu $at,$t9,$v0        ; at = (v0 > 桶哨兵 t9)'),
        (0x004D582B, 'sltu $t3,$v0,$t5        ; t3 = (v0 < 0x1FFFFFFE)，t5 由 malloc 在 0x1024BC 设定'),
        (0x002B0824, 'and $at,$at,$t3         ; at != 0 ⇔ 链头看起来是 RAM 内的块'),
        (0x10200002, 'beq $at,$zero,0x%08X    ; 不合法 -> .bad' % bad),
        (0x00000000, 'nop'),
        (jword(0x001024D0), 'j 0x001024D0            ; 合法：回原循环体'),
        (0x00000000, 'nop'),
        (jword(0x00102590), 'j 0x00102590            ; .bad：走既有的「本桶无可用块」出口'),
        (0x00000000, 'nop'),
    ]


CAVE_FN = {'OOMFIX': cave_oomfix, 'F1': cave_f1, 'F1b': cave_f1b, 'F7': cave_f7, 'F4': cave_f4}
SITE = {'OOMFIX': OOMFIX, 'F1': F1, 'F1b': F1b, 'F7': F7, 'F4': F4}

FLAVORS = {
    'A':    dict(base='layA', use=['OOMFIX'], inherit_f4=True,
                 why='F4（基底已有）+ OOMFIX：F4 bail 后 malloc 可能返回 NULL，由解压器调用侧兜底'),
    'B':    dict(base='layA', use=['OOMFIX', 'F1', 'F1b'], inherit_f4=True,
                 why='A + F1 + F1b：free() 两条同族「用不可信 prev_foot 造基址」站点都加范围+对齐校验（治因）'),
    'C':    dict(base='layA', use=['OOMFIX', 'F7'], inherit_f4=True,
                 why='A + F7：堵住本轮新病灶（own-bin 回边 0x1021D4 没有校验）'),
    '2400': dict(base='2400', use=['OOMFIX', 'F7'], inherit_f4=False,
                 why='产品线最终推荐组合 = F4（本工具打）+ OOMFIX + F7（与 COMBFIX_C 同集合；'
                     '不带 F1/F1b：它们既拦不住本次的野 free+插链，又会带来 660..810 那 6 帧像素差异）'),
}

REF_GATES = [0x00416EE8, 0x00417160, 0x0041751C, 0x005656A4]
KNOWN_CAVES = {
    'DBCS cave 全区': (0x00416E00, 0x00417800),
    'ZH cave block B': (0x00565600, 0x00565B00),
    'OOMFIX cave': (0x00550048, 0x00550080),
    'SPINFIX CAVE_F1 区': (0x0055B730, 0x0055B780),
    'SPINFIX CAVE_F2 区': (0x005DECC4, 0x005DED00),
    'SPINFIX CAVE_F4': (0x0041A35C, 0x0041A380),
    '解压器本体': (0x00539110, 0x00539310),
    '解压器调用者': (0x0051BE10, 0x0051C000),
    'RSFont 被替换区': (0x0021AC00, 0x0021AE00),
    '分配器镜像': (0x00101C00, 0x00102700),
}


def sha256_file(p, blk=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(blk), b''):
            h.update(b)
    return h.hexdigest()


def xor_crc(data):
    c = 0
    for (w,) in struct.iter_unpack('<I', data[:len(data) // 4 * 4]):
        c ^= w
    return c & 0xFFFFFFFF


def iso_root_entries(path):
    with open(path, 'rb') as f:
        f.seek(16 * SEC)
        pvd = f.read(SEC)
        assert pvd[1:6] == b'CD001'
        rlba = struct.unpack_from('<I', pvd, 158)[0]
        rsz = struct.unpack_from('<I', pvd, 166)[0]
        f.seek(rlba * SEC)
        d = f.read(rsz)
    ents, off = [], 0
    while off < len(d) and d[off]:
        rl = d[off]
        nm = d[off + 33:off + 33 + d[off + 32]].decode('latin-1').split(';')[0]
        ents.append((nm.upper(), struct.unpack_from('<I', d, off + 2)[0], struct.unpack_from('<I', d, off + 10)[0]))
        off += rl
    return ents


def read_elf_from_iso(path):
    for (nm, lba, sz) in iso_root_entries(path):
        if nm == ELF_NAME.upper():
            with open(path, 'rb') as f:
                f.seek(lba * SEC)
                d = f.read(sz)
            assert d[:4] == b'\x7fELF'
            return d, lba, sz
    raise SystemExit('ISO 里找不到 %s' % ELF_NAME)


def elf_off(va, lba=ELF_LBA):
    return va - ISO_OF_VA - lba * SEC


def word_at(elf, va, lba=ELF_LBA):
    return struct.unpack_from('<I', elf, elf_off(va, lba))[0]


def diff_runs(a, b, blk=1 << 22):
    runs, cur, off = [], None, 0
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            ba, bb = fa.read(blk), fb.read(blk)
            if not ba and not bb:
                break
            if len(ba) != len(bb):
                raise SystemExit('尺寸不同')
            if ba != bb:
                for i in range(len(ba)):
                    if ba[i] != bb[i]:
                        if cur is None:
                            cur = [off + i, bytearray(), bytearray()]
                        cur[1].append(ba[i])
                        cur[2].append(bb[i])
                    elif cur is not None:
                        runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
                        cur = None
            elif cur is not None:
                runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
                cur = None
            off += len(ba)
    if cur is not None:
        runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
    return runs


def dis_list(words, va0):
    spec = importlib.util.spec_from_file_location(
        'dis2', os.path.join(ROOT, 'work', 'builds', 'GR_CULPRIT', 'tools', 'dis2.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules['dis2'] = m
    spec.loader.exec_module(m)
    return ['  0x%08X  %08X  %s' % (va0 + 4 * i, w, m.dis(w, va0 + 4 * i)) for i, w in enumerate(words)]


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--flavor', required=True, choices=sorted(FLAVORS))
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--meta', default=None)
    a = ap.parse_args()

    spec = BASES[FLAVORS[a.flavor]['base']]
    base = os.path.join(ROOT, spec['path'])
    out = os.path.abspath(a.out)
    tag = a.tag or os.path.splitext(os.path.basename(out))[0]

    base_sha = sha256_file(base)
    base_size = os.path.getsize(base)
    base_elf, lba, elf_size = read_elf_from_iso(base)
    base_elf_sha = hashlib.sha256(base_elf).hexdigest()
    ok_sha = (base_sha == spec['sha256'])
    if not ok_sha or base_size != spec['bytes']:
        raise SystemExit('[拒绝] 基底指纹不符：%s（期望 %s）' % (base_sha, spec['sha256']))

    plan = []
    if FLAVORS[a.flavor]['inherit_f4']:
        # F4 必须已在基底里（逐字断言）
        assert word_at(base_elf, F4['va'], lba) == jword(F4['cave']), '基底里没有 F4 站点！'
        assert word_at(base_elf, F4['cave'], lba) == 0x0322082B, '基底里没有 F4 cave！'
    else:
        plan.append(F4)
    for nm in FLAVORS[a.flavor]['use']:
        plan.append(SITE[nm])

    for s in plan:
        got = word_at(base_elf, s['va'], lba)
        assert got == s['old'], '%s 原字不符：%08X != %08X' % (s['name'], got, s['old'])

    cave_rep = []
    for s in plan:
        words = [w for (w, _d) in CAVE_FN[s['name']](s['cave'])]
        eo = elf_off(s['cave'], lba)
        blob = base_elf[eo:eo + 4 * len(words)]
        assert set(blob) <= {0}, '%s cave 0x%08X 不是全零（%d 个非零字节）' % (s['name'], s['cave'], sum(1 for b in blob if b))
        cave_rep.append(dict(name=s['name'], va='0x%08X' % s['cave'], words=['0x%08X' % w for w in words],
                             iso_off='0x%08X' % (s['cave'] - ISO_OF_VA), elf_off='0x%07X' % eo,
                             bytes=4 * len(words), dis=dis_list(words, s['cave'])))

    print('=' * 100)
    print('[combfix] flavor=%s  base=%s' % (a.flavor, spec['path']))
    print('  基底 sha256=%s %s' % (base_sha, 'OK' if ok_sha else 'MISMATCH'))
    print('  ELF @LBA %d %d B sha256=%s' % (lba, elf_size, base_elf_sha))
    print('  策略：%s' % FLAVORS[a.flavor]['why'])
    for s in plan:
        print('  %-6s 站点 0x%08X / ISO 0x%08X / ELF 0x%07X : %08X (%s) -> j 0x%08X'
              % (s['name'], s['va'], s['va'] - ISO_OF_VA, elf_off(s['va'], lba), s['old'], s['dis_old'], s['cave']))
    for c in cave_rep:
        print('  %-6s cave 0x%08X (%d B, 基底全零 ✓)' % (c['name'], int(c['va'], 16), c['bytes']))
        for line in c['dis']:
            print('        ' + line)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        for s in plan:
            f.seek(s['va'] - ISO_OF_VA)
            f.write(struct.pack('<I', jword(s['cave'])))
        for c in cave_rep:
            f.seek(int(c['va'], 16) - ISO_OF_VA)
            for w in c['words']:
                f.write(struct.pack('<I', int(w, 16)))
        f.flush()
        os.fsync(f.fileno())

    out_elf, lba2, size2 = read_elf_from_iso(out)

    def ord_(va):
        return word_at(out_elf, va, lba2)

    ok_sites = all(ord_(s['va']) == jword(s['cave']) for s in plan)
    ok_caves = all(all(ord_(int(c['va'], 16) + 4 * i) == int(w, 16) for i, w in enumerate(c['words']))
                   for c in cave_rep)
    assert ok_sites and ok_caves, '回读不符'

    declared = set()
    for s in plan:
        declared.add(s['va'])
    for c in cave_rep:
        va = int(c['va'], 16)
        for i in range(len(c['words'])):
            declared.add(va + 4 * i)

    refs, ref_ok = [], True
    for (why, (lo, hi)) in KNOWN_CAVES.items():
        e0, e1 = elf_off(lo, lba), elf_off(hi, lba)
        n = e1 - e0
        if base_elf[e0:e0 + n] == out_elf[e0:e0 + n]:
            refs.append(dict(why=why, va_lo='0x%08X' % lo, va_hi='0x%08X' % hi, identical=True,
                             note='未使用本区，逐字节相同'))
            continue
        b = bytearray(base_elf[e0:e0 + n])
        for va in declared:
            if lo <= va < hi:
                b[elf_off(va, lba) - e0:elf_off(va, lba) - e0 + 4] = struct.pack('<I', ord_(va))
        same = (bytes(b) == out_elf[e0:e0 + n])
        refs.append(dict(why=why, va_lo='0x%08X' % lo, va_hi='0x%08X' % hi, identical=bool(same),
                         note='本盘在此区有声明窗口，除声明字外逐字节相同'))
        ref_ok = ref_ok and same
    head_ok = (base_elf[0:0x1000] == out_elf[0:0x1000])
    gates = ['0x%08X=0x%08X' % (g, ord_(g)) for g in REF_GATES]
    gates_ok = all(ord_(g) == word_at(base_elf, g, lba) for g in REF_GATES)
    assert gates_ok and ref_ok and head_ok, '参照区/闸门/ELF 头被动'

    runs = diff_runs(base, out)
    win = [(s['va'] - ISO_OF_VA, s['va'] - ISO_OF_VA + 4) for s in plan] + \
          [(int(c['va'], 16) - ISO_OF_VA, int(c['va'], 16) - ISO_OF_VA + c['bytes']) for c in cave_rep]
    inwin = all(any(lo <= o and o + len(ob) <= hi for (lo, hi) in win) for (o, ob, _n) in runs)
    nb = sum(len(ob) for (_o, ob, _n) in runs)
    touched = sum(1 for (lo, hi) in win if any(lo <= o < hi for (o, _ob, _n) in runs))
    out_sha = sha256_file(out)
    out_size = os.path.getsize(out)
    iso_crc = xor_crc(out_elf)

    rep = dict(tag=tag, flavor=a.flavor, strategy=FLAVORS[a.flavor]['why'],
               tool=r'work\builds\GR_COMBFIX\tools\combfix_apply.py',
               base_file=os.path.relpath(base, ROOT), base_sha256=base_sha, base_bytes=base_size,
               base_elf_sha256=base_elf_sha, base_elf_lba=lba, base_elf_bytes=elf_size,
               inherited_patches=(
                   [dict(name='F4（继承自基底）', va='0x%08X' % F4['va'], iso_off='0x%08X' % (F4['va'] - ISO_OF_VA),
                         elf_off='0x%07X' % elf_off(F4['va'], lba), old_word='0x%08X' % F4['old'],
                         old_dis=F4['dis_old'], new_word='0x%08X' % jword(F4['cave']),
                         new_dis='j 0x%08X' % F4['cave'],
                         cave=dict(va='0x%08X' % F4['cave'], bytes=36,
                                   words=['0x%08X' % word_at(base_elf, F4['cave'] + 4 * i, lba) for i in range(9)]))
                    ] if FLAVORS[a.flavor]['inherit_f4'] else []),
               sites=[dict(name=s['name'], va='0x%08X' % s['va'], iso_off='0x%08X' % (s['va'] - ISO_OF_VA),
                           elf_off='0x%07X' % elf_off(s['va'], lba), old_word='0x%08X' % s['old'],
                           old_dis=s['dis_old'], new_word='0x%08X' % jword(s['cave']),
                           new_dis='j 0x%08X' % s['cave'], exits=s['resume_dis'],
                           delay_slot=dict(va='0x%08X' % (s['va'] + 4),
                                           word='0x%08X' % word_at(base_elf, s['va'] + 4, lba),
                                           note='未改；F1b/F7 的语义已把延迟槽的副作用算进去'))
                      for s in plan],
               caves=cave_rep, ref_regions=refs, gates_readback=gates,
               elf_header_identical=bool(head_ok),
               out=os.path.relpath(out, ROOT), out_file=os.path.basename(out),
               bytes=out_size, sha256=out_sha, elf_sha256=hashlib.sha256(out_elf).hexdigest(),
               elf_crc32_xor='%08X' % iso_crc,
               savestate_name='SLUS-20613 (%08X).01.p2s' % iso_crc,
               diff_runs=[dict(iso_off='0x%08X' % o, len=len(ob), old=ob.hex(), new=nb2.hex())
                          for (o, ob, nb2) in runs],
               diff_run_count=len(runs), diff_bytes=nb,
               selfcheck=dict(size_unchanged=(out_size == base_size),
                              diff_only_in_declared_windows=bool(inwin),
                              every_window_touched=(touched == len(win)),
                              readback_all_ok=bool(ok_sites and ok_caves),
                              gates_untouched_4=bool(gates_ok),
                              dbcs_zh_other_caves_untouched=bool(ref_ok),
                              elf_header_untouched=bool(head_ok),
                              elf_lba_size_unchanged=(lba2 == lba and size2 == elf_size)))
    print('\n[写出] %s  (%d B)' % (out, out_size))
    print('  sha256 = %s' % out_sha)
    print('  ELF sha256 = %s' % rep['elf_sha256'])
    print('  PCSX2 CRC = %08X  ⇒ 存档名 %s' % (iso_crc, rep['savestate_name']))
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
    return 0 if (inwin and ok_sites and ok_caves and gates_ok and ref_ok and head_ok
                 and out_size == base_size and touched == len(win)) else 1


if __name__ == '__main__':
    sys.exit(main())
