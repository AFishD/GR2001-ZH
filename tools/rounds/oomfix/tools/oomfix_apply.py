# -*- coding: utf-8 -*-
r"""oomfix_apply.py —— 【GR_OOMFIX】把「解压器 NULL 检查」修复（F1+F2）打到成品盘上。

根因（`docs\REPORT_CULPRIT_STORE.md`，本工具不再重查）
------------------------------------------------------
`0x00539110`（游戏自己的 LZ77 解压器）在
    0x0053916C  jal 0x00102D40        ; malloc(s0+1)
    0x00539170  addiu a0,s0,1         ; 延迟槽：请求 0x10011
    0x00539174  sw v0,4(s3)           ; sink[4] = 输出缓冲基址   ← 不检查 NULL
    0x00539178  sw v0,8(s3)           ; sink[8] = 输出游标
之后把解压输出逐字节写到 NULL+0：0x0..0x300（异常向量区）与 0x1300 被覆盖 ⇒ 第 45 帧 Trap。

修复
----
F1  0x00539174  AE620004 (sw $v0,4($s3))  ->  08154012 (j 0x00550048)
    ★ `j` 的延迟槽 = 0x00539178 原指令 `sw $v0,8($s3)`，**照常执行**：
      成功时写入正确基址（cave 里再写一次，等价）；失败时写入 0（正是失败态该有的值）。
      因此延迟槽无需改动，行为与「两条 store 都搬进 cave」等价（cave 里仍保留两条，
      保证成功路径的写入序列与原版逐条一致）。
F2  cave @ 0x00550048（原盘全零区，见下），11 条 = 44 B：
      0x00550048  beq  $v0,$zero, .fail      ; malloc 返回 0 ?
      0x0055004C  nop
      0x00550050  sw   $v0, 4($s3)           ; 成功：原逻辑
      0x00550054  sw   $v0, 8($s3)
      0x00550058  j    0x0053917C            ; 回原流程
      0x0055005C  nop
      .fail:
      0x00550060  sw   $zero, 4($s3)         ; 基址/游标 = 0（结构自洽）
      0x00550064  sw   $zero, 8($s3)
      0x00550068  daddu $s0, $zero, $zero    ; ★ s0 = 0
      0x0055006C  j    0x005392A0            ; 走既有尾声：pcpyld v0,s0,zero ⇒ 返回 0
      0x00550070  nop

★ 不改 0x005392A0（F3：调用者把返回值当尺寸参与 divu/sll/subu 算术）。
★ 不改 0x004039C8（F4：memcpy 库函数，169 处调用）。
★ 调用者 0x0051BE10 的失败分支是现成的：`sw v0,52(s1)` → `bne v0,zero,0x51BED8`
  ⇒ v0==0 时走 0x51BEBC：free(s1[0x14]) → 清 0 → sink 析构 0x5392C0(a1=-1) → s0=0 →
  0x51BEF0 `beq s0,zero,0x51BFA4` → 跳过后续 ⇒ **该资源被跳过，游戏继续**。

cave 选址理由（0x00550048..0x00550080，56 B；本工具只用前 44 B）
---------------------------------------------------------------
* 原盘/两基底**逐字节全零**（本工具会断言）；
* `.symtab` 里**没有任何符号**覆盖或紧邻这段（上一条函数在 0x00550040 `j 0x0054FF68`
  + 延迟槽 `addiu sp,sp,0x30` 收尾 ⇒ **不可能线性落入**；下一段代码/微码从 0x00550080 起）；
* 全 .text（只扫 FUNC 符号覆盖的地址）**没有**任何 j/jal/分支目标落在 0x550040..0x5500C0；
* 装载段内**没有** 32 位字面量指向该区间，`.relmain` 20 万条重定位**没有**一条落点在此；
* lui+addiu/ori 合成地址扫描：整个 0x54FF00..0x550200 只有 1 处引用（0x005500F0，VU0 微码），
  **不涉及**本区间；
* 与 DBCS cave 全区（0x416E00..0x417800）、4 个闸门站点、ZH cave block B（0x565600..0x565B00）
  及既知挂点**无重叠**。

自证
----
尺寸不变 / 全盘 diff 只落在声明窗口 / 每个窗口都被写到 / 产物回读逐字相符 /
4 个闸门 + DBCS cave 区 + ZH cave 区 + ELF 头逐字节未动 / ELF LBA 与大小不变。

只读基底；只写 --out 与 --meta 指定的文件。
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys

SEC = 2048
ELF_NAME = 'SLUS_206.13'
ISO_OF_VA = 0x6C780        # ISO 偏移 = VA − 0x6C780（由 PT_LOAD off=0x80 va=0x100000、LBA295 推出）

# 基底指纹（不符即拒绝）
BASES = {
    '2400': dict(path=r'work\builds\GR_REBUILD\GR_REBUILD2400.iso',
                 sha256='d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0',
                 elf_sha256='5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8',
                 bytes=1648164864),
    'lay1': dict(path=r'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso',
                 sha256='a69a9ca44049eaed4085239a2b8d10af58888f54f62a51e40c1ece22dd2d2808',
                 elf_sha256='0a986bb375176df41fad67798423f2e1a0a1c902d181ab9d673627a6d98387b9',
                 bytes=1648164864),
}

# ── F1：唯一入口 ────────────────────────────────────────────────────────────────
F1_VA = 0x00539174
F1_OLD = 0xAE620004                      # sw $v0,4($s3)
CAVE_VA = 0x00550048
F1_NEW = 0x08000000 | (CAVE_VA >> 2)     # j 0x00550048
RESUME_VA = 0x0053917C                   # 原流程续点（0x539178 之后）
EPILOGUE_VA = 0x005392A0                 # 既有尾声：pcpyld v0,s0,zero / ld ra / jr ra

# ── F2：cave 体（11 字 = 44 B） ─────────────────────────────────────────────────
FAIL_VA = CAVE_VA + 0x18
CAVE = [
    (0x10400005, 'beq $v0,$zero,.fail   (0x%08X)' % FAIL_VA),
    (0x00000000, 'nop'),
    (0xAE620004, 'sw $v0,4($s3)         ; 成功：输出缓冲基址'),
    (0xAE620008, 'sw $v0,8($s3)         ; 成功：输出游标'),
    (0x08000000 | (RESUME_VA >> 2), 'j 0x%08X          ; 回原流程' % RESUME_VA),
    (0x00000000, 'nop'),
    (0xAE600004, 'sw $zero,4($s3)       ; .fail：基址 = 0'),
    (0xAE600008, 'sw $zero,8($s3)       ; .fail：游标 = 0'),
    (0x0000802D, 'daddu $s0,$zero,$zero ; ★ s0 = 0 ⇒ 返回值 0'),
    (0x08000000 | (EPILOGUE_VA >> 2), 'j 0x%08X          ; 走既有尾声' % EPILOGUE_VA),
    (0x00000000, 'nop'),
]
CAVE_BYTES = 4 * len(CAVE)               # 44
CAVE_WINDOW = (CAVE_VA, CAVE_VA + CAVE_BYTES)

# ── 必须逐字节不变的参照区 ──────────────────────────────────────────────────────
REF_GATES = [0x00416EE8, 0x00417160, 0x0041751C, 0x005656A4]     # 4 个 DBCS 闸门
REF_REGIONS = [
    (0x00416E00, 0x00417800, 'DBCS cave 全区（iomanX 死代码被汉化 cave 覆盖）'),
    (0x00565600, 0x00565B00, 'ZH cave block B'),
    (0x00539110, 0x00539310, '解压器本体（除 F1 声明窗口外必须与基底相同）'),
    (0x0051BE10, 0x0051C000, '调用者 0x0051BE10'),
    (0x0021AC00, 0x0021AE00, 'RSFont 被替换函数区'),
]
REF_HEAD = (0, 0x1000)                   # ELF 头 + program headers


def sha256_file(p, blk=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(blk), b''):
            h.update(b)
    return h.hexdigest()


def iso_find_elf(f):
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    assert pvd[1:6] == b'CD001', '扇区 16 不是 ISO9660 PVD'
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
        if name in (ELF_NAME + ';1', ELF_NAME):
            return ext, sz
        off += ln
    raise SystemExit('ISO 目录里找不到 %s' % ELF_NAME)


def read_elf(path):
    with open(path, 'rb') as f:
        lba, size = iso_find_elf(f)
        f.seek(lba * SEC)
        d = f.read(size)
    assert d[:4] == b'\x7fELF'
    return d, lba, size


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


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--flavor', required=True, choices=sorted(BASES))
    ap.add_argument('--base', default=None, help='默认取 BASES[flavor].path')
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--meta', default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    spec = BASES[a.flavor]
    base = os.path.abspath(a.base or spec['path'])
    out = os.path.abspath(a.out)
    if base == out:
        raise SystemExit('--out 不能等于基底')
    tag = a.tag or os.path.splitext(os.path.basename(out))[0]

    # ── 1) 基底校验 ────────────────────────────────────────────────────────
    base_sha = sha256_file(base)
    base_size = os.path.getsize(base)
    base_elf, lba, elf_size = read_elf(base)
    base_elf_sha = hashlib.sha256(base_elf).hexdigest()
    rep = dict(tag=tag, flavor=a.flavor, tool=r'work\builds\GR_OOMFIX\tools\oomfix_apply.py',
               base_file=base, base_sha256=base_sha, base_bytes=base_size,
               base_elf_sha256=base_elf_sha, base_elf_lba=lba, base_elf_bytes=elf_size,
               expected_base_sha256=spec['sha256'], expected_base_elf_sha256=spec['elf_sha256'],
               warnings=[])
    ok_sha = (base_sha == spec['sha256'])
    ok_elf = (base_elf_sha == spec['elf_sha256'])
    if not a.force and not (ok_sha and ok_elf and base_size == spec['bytes']):
        raise SystemExit('[拒绝] 基底指纹不符：\n  iso  sha256=%s（期望 %s）\n  elf  sha256=%s（期望 %s）'
                         % (base_sha, spec['sha256'], base_elf_sha, spec['elf_sha256']))
    if not ok_sha:
        rep['warnings'].append('基底 ISO sha256 与声明不符（--force 放行）')
    if not ok_elf:
        rep['warnings'].append('基底 ELF sha256 与声明不符（--force 放行）')

    def bword(va):
        o = va - ISO_OF_VA
        return struct.unpack_from('<I', base_elf, o - lba * SEC)[0]

    # ── 2) 站点核对 ────────────────────────────────────────────────────────
    got = bword(F1_VA)
    assert got == F1_OLD, 'F1 原字不符：0x%08X ≠ 0x%08X' % (got, F1_OLD)
    cave_old = base_elf[CAVE_WINDOW[0] - ISO_OF_VA - lba * SEC:
                        CAVE_WINDOW[1] - ISO_OF_VA - lba * SEC]
    assert set(cave_old) <= {0}, 'cave 落点不是全零！%s' % cave_old[:16].hex()
    rep['f1'] = dict(va='0x%08X' % F1_VA, iso_off='0x%08X' % (F1_VA - ISO_OF_VA),
                     elf_off='0x%07X' % (F1_VA - ISO_OF_VA - lba * SEC),
                     old_word='0x%08X' % F1_OLD, new_word='0x%08X' % F1_NEW,
                     dis_old='sw $v0,4($s3)',
                     dis_new='j 0x%08X（cave）' % CAVE_VA,
                     delay_slot=dict(va='0x%08X' % (F1_VA + 4),
                                     word='0x%08X' % bword(F1_VA + 4),
                                     note='j 的延迟槽 = 原 sw $v0,8($s3)，**未改**；'
                                          '成功时写正确基址、失败时写 0，两者都与 cave 一致'))
    rep['f2'] = dict(cave_va='0x%08X' % CAVE_VA, cave_iso_off='0x%08X' % (CAVE_VA - ISO_OF_VA),
                     cave_elf_off='0x%07X' % (CAVE_VA - ISO_OF_VA - lba * SEC),
                     bytes=CAVE_BYTES, window='0x%08X..0x%08X' % CAVE_WINDOW,
                     region_all_zero_in_base=True,
                     words=[dict(va='0x%08X' % (CAVE_VA + 4 * i), word='0x%08X' % w, dis=d)
                            for i, (w, d) in enumerate(CAVE)],
                     window_total_zero_region='0x00550048..0x00550080 (56 B)，本补丁只用前 44 B')
    rep['f3_untouched'] = dict(va='0x%08X' % EPILOGUE_VA, word='0x%08X' % bword(EPILOGUE_VA),
                               note='未改：调用者把该返回值当尺寸参与算术')
    rep['f4_untouched'] = dict(va='0x004039C8', word='0x%08X' % bword(0x004039C8),
                               note='未改：库 memcpy，169 处调用')

    print('=' * 96)
    print('[oomfix] flavor=%s' % a.flavor)
    print('  基底 %s' % base)
    print('       sha256=%s %s' % (base_sha, 'OK' if ok_sha else 'MISMATCH'))
    print('  ELF  @LBA %d %d B sha256=%s %s' % (lba, elf_size, base_elf_sha,
                                                'OK' if ok_elf else 'MISMATCH'))
    print('  F1   0x%08X / ISO 0x%08X : %08X -> %08X  (j 0x%08X)'
          % (F1_VA, F1_VA - ISO_OF_VA, F1_OLD, F1_NEW, CAVE_VA))
    print('  F2   cave 0x%08X (%d B, 基底全零 ✓)' % (CAVE_VA, CAVE_BYTES))
    for i, (w, d) in enumerate(CAVE):
        print('       0x%08X  %08X  %s' % (CAVE_VA + 4 * i, w, d))

    # ── 3) 写产物 ─────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        f.seek(F1_VA - ISO_OF_VA)
        f.write(struct.pack('<I', F1_NEW))
        f.seek(CAVE_VA - ISO_OF_VA)
        for (w, _d) in CAVE:
            f.write(struct.pack('<I', w))
        f.flush()
        os.fsync(f.fileno())

    # ── 4) 回读 + 参照区 + 差异窗口 ────────────────────────────────────────
    out_elf, lba2, size2 = read_elf(out)

    def ord_(va):
        return struct.unpack_from('<I', out_elf, va - ISO_OF_VA - lba2 * SEC)[0]

    rb_f1 = (ord_(F1_VA) == F1_NEW)
    rb_cave = all(ord_(CAVE_VA + 4 * i) == w for i, (w, _d) in enumerate(CAVE))
    assert rb_f1 and rb_cave, '回读不符'
    rep['readback'] = dict(f1='0x%08X' % ord_(F1_VA),
                           cave=['0x%08X' % ord_(CAVE_VA + 4 * i) for i in range(len(CAVE))],
                           all_ok=bool(rb_f1 and rb_cave))
    # 参照区逐字节
    refs = []
    ref_ok = True
    checks = [(0, 0x1000, 'ELF 头 + program headers（ELF 文件偏移 0..0x1000）')]
    for (lo, hi, why) in REF_REGIONS:
        checks.append((lo - ISO_OF_VA - lba * SEC, hi - ISO_OF_VA - lba * SEC, why))
    for (o0, o1, why) in checks:
        n = o1 - o0
        same = base_elf[o0:o0 + n] == out_elf[o0:o0 + n]
        # F1 声明窗口在「解压器本体」参照区里，单独允许
        f1_elf = F1_VA - ISO_OF_VA - lba * SEC
        if not same and o0 <= f1_elf < o1:
            b = bytearray(base_elf[o0:o0 + n])
            b[f1_elf - o0:f1_elf - o0 + 4] = struct.pack('<I', F1_NEW)
            same = (bytes(b) == out_elf[o0:o0 + n])
        refs.append(dict(elf_off='0x%07X' % o0, elf_end='0x%07X' % o1, why=why,
                         identical=bool(same)))
        ref_ok = ref_ok and same
    rep['ref_regions'] = refs
    rep['gates_readback'] = ['0x%08X=0x%08X' % (g, ord_(g)) for g in REF_GATES]
    gates_ok = all(ord_(g) == bword(g) for g in REF_GATES)
    rep['elf_header_identical'] = (base_elf[0:0x1000] == out_elf[0:0x1000])
    assert gates_ok, '闸门被动了！'
    assert ref_ok, '参照区被动了！'

    runs = diff_runs(base, out)
    win = [(F1_VA - ISO_OF_VA, F1_VA - ISO_OF_VA + 4),
           (CAVE_WINDOW[0] - ISO_OF_VA, CAVE_WINDOW[1] - ISO_OF_VA)]
    inwin = all(any(lo <= o and o + len(ob) <= hi for (lo, hi) in win) for (o, ob, _n) in runs)
    nbytes = sum(len(ob) for (_o, ob, _n) in runs)
    touched = sum(1 for (lo, hi) in win if any(lo <= o < hi for (o, _ob, _n) in runs))
    out_sha = sha256_file(out)
    out_size = os.path.getsize(out)

    rep.update(out=os.path.relpath(out, os.path.abspath(os.path.join(
                     os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))),
               out_file=os.path.basename(out), bytes=out_size, sha256=out_sha,
               out_elf_sha256=hashlib.sha256(out_elf).hexdigest(),
               iso_offsets=['0x%08X' % (F1_VA - ISO_OF_VA),
                            '0x%08X' % (CAVE_WINDOW[0] - ISO_OF_VA)],
               diff_runs=[dict(iso_off='0x%08X' % o, len=len(ob), old=ob.hex(), new=nb.hex())
                          for (o, ob, nb) in runs],
               diff_run_count=len(runs), diff_bytes=nbytes,
               selfcheck=dict(size_unchanged=(out_size == base_size),
                              diff_only_in_declared_windows=bool(inwin),
                              every_window_touched=(touched == len(win)),
                              readback_all_ok=bool(rb_f1 and rb_cave),
                              gates_untouched_4=bool(gates_ok),
                              dbcs_cave_and_zh_cave_untouched=bool(
                                  all(r['identical'] for r in refs
                                      if 'cave' in r['why'] or 'RSFont' in r['why'])),
                              elf_header_untouched=bool(rep['elf_header_identical']),
                              elf_lba_size_unchanged=(lba2 == lba and size2 == elf_size)))
    print('\n[写出] %s  (%d B, sha256=%s)' % (out, out_size, out_sha))
    print('  ELF  sha256 = %s' % rep['out_elf_sha256'])
    print('  diff = %d run / %d B；声明窗口外 %d run'
          % (len(runs), nbytes, 0 if inwin else -1))
    for r in runs:
        print('    0x%08X +%d  %s -> %s' % (r[0], len(r[1]), r[1].hex(), r[2].hex()))
    for k, v in rep['selfcheck'].items():
        print('  自证 %-36s %s' % (k, 'OK' if v else 'FAIL'))
    print('  闸门回读 %s' % ' / '.join(rep['gates_readback']))
    mp = a.meta or (os.path.splitext(out)[0] + '.meta.json')
    with open(mp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('[meta] %s' % mp)
    return 0 if (inwin and rb_f1 and rb_cave and gates_ok and ref_ok
                 and out_size == base_size and touched == len(win)) else 1


if __name__ == '__main__':
    sys.exit(main())
