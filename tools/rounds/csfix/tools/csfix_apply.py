# -*- coding: utf-8 -*-
r"""csfix_apply.py —— GR_CSFIX：把「图标特判永不命中」的**代码侧修复**打到 2,400 成品盘。

判据（沿用 `REPORT_SENTINEL.md` §S5.4.3 / `REPORT_SENTINEL_FIX.md`）：
    原字 `addiu rX,zero,0x00B1 / 0x00B5 / 0xFFB1 / 0xFFB5`
    新字 `addiu rX,zero,0xFF00`（⇒ rX = 0xFFFFFF00）
    0xFFFFFF00 既不在 `lb` 的符号扩展集合（0xFFFFFF80..0xFFFFFFFF ∪ 0..0x7F）里，
    也不在 `lhu` 的零扩展集合（0..0xFFFF）里 ⇒ **两种口径都永不命中**。

★ 本工具**只改 ELF 内的 9 处立即数**（18 字节），不碰 charset / 文本 / 图集 / 容器 / 目录。

三种输入模式：
  --elf   <k2.elf>  --out <csfix.elf>     ELF 直改（离线核验；不需要 ISO）
  --iso   <k2.iso>  --out <csfix.iso>     ★ 正式出盘（A 盘），先按 sha256 校验基底
  --bdump <*.dump>  --out <csfix.elf>     从 PCSX2 CDVD 块转储里取回 K2 的 ELF 再改

基底指纹（**不符即拒绝**；`--force` 可跳过，但会登记）：
  GR_FA2400_K2.iso          sha256 c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94
                            size   1,648,164,864 B
  SLUS_206.13（K2 盘内）    sha256 5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8
                            size   37,453,732 B

站点（9 处「活 + 会改变行为」；默认只打这 9 处 = **最小差异**）：
  VA          ISO 偏移    原字        角色
  0x219C08    0x1AD488    240300B5    DrawString 第 1 次判定（0xB5）⇒ 硬编码图标 UV
  0x219C10    0x1AD490    240300B5    上一条的**延迟槽副本**（0xB5 分支被采纳时它就是被比较值）
  0x219C14    0x1AD494    240300B1    DrawString 第 1 次判定（0xB1）
  0x219C94    0x1AD514    240300B5    DrawString 第 2 次判定（0xB5）⇒ 字距走图标专用块
  0x219CAC    0x1AD52C    240300B1    DrawString 第 2 次判定（0xB1）
  0x219D24    0x1AD5A4    240200B5    DrawString 第 3 次判定（0xB5）⇒ AddOneWord(t0=1) 副包
  0x219D38    0x1AD5B8    240200B1    DrawString 第 3 次判定（0xB1）
  0x416F5C    0x3AA7DC    240900B5    ★ CharWidth cave（0x416F40）自己的图标特判（0xB5）
  0x416F68    0x3AA7E8    240900B1    ★ CharWidth cave 自己的图标特判（0xB1）

**排除在外（登记，不写进最小差异）**——实测判定见 `audit/sites_k2.md`：
  0x219C40  2403FFB5  **惰性**：只从 `0x219C18 beq $a1,0x00B1` 进入 ⇒ 到 0x219C40 时 $a1 ≡ 0x00B1，
                      而 `0x219C44 bne $a1,$v1` 的 $v1 = 0xFFFFFFB5 ⇒ **恒不相等**（改 0xFF00 后
                      0xFFFFFF00 仍 ≠ 0x00B1 ⇒ 分支走向完全不变）
  0x21AD38  2402FFB5  **死代码**：`0x21AD10` 已换成 trampoline `addiu sp,sp,-16; sd ra,0(sp);
                      j 0x416F40`；`sent_reach` 实测进入 [0x21AD20,0x21ADD8) 的 8 条控制流
                      **全部来自区间内部** ⇒ 0 条外部入口
  0x21AD4C  2402FFB1  同上（死代码）
  `--all12` 可把这三处一并改成 0xFF00（= 与 `SENT_06` 同型的「全 ELF 无残留」变体；
  行为与 9 处版**完全等价**，只多 6 个字节的差异）。

只读基底；只写 --out 指定的文件与 --meta 指定的 json。
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_CSFIX')

ISO_OF_VA = 0x6C780            # ISO = VA − 0x6C780（由第一个 PT_LOAD 推出，本工具会自检）
ELF_OF_VA = 0xFFF80            # ELF 文件偏移 = VA − 0xFFF80（PT_LOAD off=0x80 / va=0x100000）
ELF_IN_ISO = 0x93800           # K2 盘里 ELF 头所在的 ISO 偏移（= 0xFFF80 − 0x6C780）
SAFE = 0xFF00

K2_ISO_SHA = 'c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94'
K2_ISO_SIZE = 1648164864
K2_ELF_SHA = '5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8'
K2_ELF_SIZE = 37453732

# (VA, 原字, 角色, 可达性)：live = 参与判定；inert/dead = 登记但不改
SITES = (
    (0x219C08, 0x240300B5, 'DrawString 第 1 次判定（0xB5）⇒ 命中走硬编码图标 UV + 图标字距', 'live'),
    (0x219C10, 0x240300B5, '0x219C0C beq 的**延迟槽副本**：0xB5 分支被采纳时 0x219C44 比的就是它',
     'live'),
    (0x219C14, 0x240300B1, 'DrawString 第 1 次判定（0xB1）⇒ 分流到 0x219C40', 'live'),
    (0x219C94, 0x240300B5, 'DrawString 第 2 次判定（0xB5）⇒ 字距走图标专用块', 'live'),
    (0x219CAC, 0x240300B1, 'DrawString 第 2 次判定（0xB1）', 'live'),
    (0x219D24, 0x240200B5, 'DrawString 第 3 次判定（0xB5）⇒ `AddOneWord(...,t0=1)` 容量 2 副包', 'live'),
    (0x219D38, 0x240200B1, 'DrawString 第 3 次判定（0xB1）', 'live'),
    (0x416F5C, 0x240900B5, '★ CharWidth cave（0x416F40）图标特判（0xB5，仅单字节 a1>>8==0 时）',
     'live'),
    (0x416F68, 0x240900B1, '★ CharWidth cave 图标特判（0xB1，仅单字节）', 'live'),
)
EXCLUDED = (
    (0x219C40, 0x2403FFB5, 'DrawString 0xB1 分支入口的「再比一次」',
     'inert：只从 0x219C18（$a1≡0x00B1）进入 ⇒ 与 0xFFFFFFB5 恒不相等；改 0xFF00 走向不变'),
    (0x21AD38, 0x2402FFB5, 'CharWidth 残留体（死）硬编码字距 20（0xB5）',
     'dead：0x21AD10 已是 trampoline ⇒ 无外部入口（sent_reach 实测 8/8 内部）'),
    (0x21AD4C, 0x2402FFB1, 'CharWidth 残留体（死）硬编码字距 20（0xB1）', 'dead：同上'),
)
# 4 个闸门（`sltiu …,0xBA`）：**不是相等比较**，是 DBCS lead 区间上界 ⇒ 绝不许动
GATES = ((0x416EE8, 0x2CA900BA, 'sltiu $t1,$a1,0xBA'),
         (0x417160, 0x2D0900BA, 'sltiu $t1,$t0,0xBA'),
         (0x41751C, 0x2D4B00BA, 'sltiu $t3,$t2,0xBA'),
         (0x5656A4, 0x2D6C00BA, 'sltiu $t4,$t3,0xBA'))
# K2 相对其基底 GR_ZH124 的另外 4 个几何字节（本工具**不动**，但回读登记）
K2_GEOM = ((0x4170AC, 0x240E0040, 'COLS 62→64'), (0x4170E8, 0x25AD0002, 'SKIP_ROWS 3→2'),
           (0x4170F8, 0x25CD0003, 'Y0 2→3'), (0x4170FC, 0x25CE0013, 'V1=V0+16 : 18→19'))
# 补丁后必须「0xB1/0xB5 立即数残留」= **仅剩声明的排除项** 的区间（活代码所在函数/cave/残留体）
RESIDUAL = (('DrawString', 0x219A70, 0x219E00),
            ('CharWidth 残留体（死）', 0x21AD10, 0x21ADD8),
            ('CharWidth cave', 0x416F40, 0x417050))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def diff_runs(a, b):
    runs = []
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        off = 0
        while True:
            ba, bb = fa.read(1 << 22), fb.read(1 << 22)
            if not ba and not bb:
                break
            n = min(len(ba), len(bb))
            i = 0
            while i < n:
                if ba[i] != bb[i]:
                    j = i
                    while j < n and ba[j] != bb[j]:
                        j += 1
                    runs.append([off + i, j - i])
                    i = j
                else:
                    i += 1
            off += n
    return runs


def load_bdump_elf(dump):
    """从 PCSX2 BDV2 块转储里按 ISO9660 目录取回 SLUS_206.13（只读）。"""
    n = os.path.getsize(dump)
    idx = {}
    with open(dump, 'rb') as f:
        magic, bsz, total, _z = struct.unpack('<4sIII', f.read(16))
        assert magic == b'BDV2' and bsz == 2048, '不是 BDV2 块转储'
        cnt, rem = divmod(n - 16, 2052)
        assert rem == 0, '长度自检失败'
        for i in range(cnt):
            f.seek(16 + i * 2052)
            idx[struct.unpack('<I', f.read(4))[0]] = 16 + i * 2052 + 4
        # ISO9660 PVD → root dir → SLUS_206.13
        def sec(lba):
            f.seek(idx[lba])
            return f.read(2048)
        root = sec(16)[156:190]
        rlba, rsize = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
        blob = b''.join(sec(rlba + i) for i in range((rsize + 2047) // 2048))
        off, found = 0, None
        while off < len(blob):
            ln = blob[off]
            if ln == 0:
                off = (off // 2048 + 1) * 2048
                continue
            rec = blob[off:off + ln]
            nm = rec[33:33 + rec[32]].decode('latin-1').upper()
            if nm.startswith('SLUS_206.13'):
                found = (struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0])
            off += ln
        assert found, '目录里没有 SLUS_206.13'
        lba, size = found
        cnt2 = (size + 2047) // 2048
        miss = [l for l in range(lba, lba + cnt2) if l not in idx]
        assert not miss, '块转储缺 %d 个扇区（例 %s）' % (len(miss), miss[:6])
        out = bytearray()
        for i in range(cnt2):
            f.seek(idx[lba + i])
            out += f.read(2048)
    return bytes(out[:size]), lba, size


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--elf')
    g.add_argument('--iso')
    g.add_argument('--bdump')
    ap.add_argument('--out', required=True)
    ap.add_argument('--meta', default=None)
    ap.add_argument('--all12', action='store_true', help='连惰性/死代码 3 处一起改（SENT_06 同型）')
    ap.add_argument('--force', action='store_true', help='跳过基底 sha256 校验（会登记）')
    a = ap.parse_args()

    mode = 'elf' if a.elf else ('iso' if a.iso else 'bdump')
    sites = list(SITES) + (list(EXCLUDED) if a.all12 else [])
    rep = dict(tool='work\\builds\\GR_CSFIX\\tools\\csfix_apply.py', mode=mode,
               declared_sites=len(sites), all12=bool(a.all12),
               safe_imm='0x%04X' % SAFE, base_check={}, warnings=[])

    # ── 1) 取基底缓冲（ELF 偏移空间）+ 校验 ───────────────────────────────
    tmp_ref = None
    if mode == 'iso':
        sha, size = sha256_file(a.iso), os.path.getsize(a.iso)
        rep['base_check'] = dict(path=os.path.relpath(a.iso, ROOT), sha256=sha, size=size,
                                 expected_sha256=K2_ISO_SHA, expected_size=K2_ISO_SIZE)
        if not a.force and (sha != K2_ISO_SHA or size != K2_ISO_SIZE):
            raise SystemExit('[拒绝] 基底不是 GR_FA2400_K2.iso：sha256=%s size=%d\n'
                             '        期望 %s / %d（确要强改加 --force）'
                             % (sha, size, K2_ISO_SHA, K2_ISO_SIZE))
        if sha != K2_ISO_SHA:
            rep['warnings'].append('基底 sha256 与声明的 K2 不符（--force 放行）')
        org = 'iso'
        ref_path, ref_size = a.iso, size
        src_of_va = lambda va: va - ISO_OF_VA                       # noqa: E731
    elif mode == 'elf':
        sha, size = sha256_file(a.elf), os.path.getsize(a.elf)
        rep['base_check'] = dict(path=os.path.relpath(a.elf, ROOT), sha256=sha, size=size,
                                 expected_sha256=K2_ELF_SHA, expected_size=K2_ELF_SIZE)
        if not a.force and (sha != K2_ELF_SHA or size != K2_ELF_SIZE):
            raise SystemExit('[拒绝] 基底不是 K2 的 SLUS_206.13：sha256=%s size=%d' % (sha, size))
        if sha != K2_ELF_SHA:
            rep['warnings'].append('基底 sha256 与声明的 K2 ELF 不符（--force 放行）')
        org = 'elf'
        ref_path, ref_size = a.elf, size
        src_of_va = lambda va: va - ELF_OF_VA                       # noqa: E731
    else:
        data, lba, size = load_bdump_elf(a.bdump)
        sha = hashlib.sha256(data).hexdigest()
        rep['base_check'] = dict(path=os.path.relpath(a.bdump, ROOT), bdump_elf_lba=lba,
                                 sha256=sha, size=size, expected_sha256=K2_ELF_SHA,
                                 expected_size=K2_ELF_SIZE)
        assert sha == K2_ELF_SHA, '块转储里的 SLUS_206.13 不是 K2 的（sha256=%s）' % sha
        org = 'bdump'
        # 差异基准 = **从转储里取回的未修改 ELF**（落到 temp，只在需要时生成）
        tmp_ref = os.path.join(OUTDIR, 'temp', '_bdump_base_SLUS_206.13.elf')
        os.makedirs(os.path.dirname(tmp_ref), exist_ok=True)
        open(tmp_ref, 'wb').write(data)
        ref_path, ref_size = tmp_ref, size
        src_of_va = lambda va: va - ELF_OF_VA                       # noqa: E731

    # ── 2) 逐站点核对原字 ────────────────────────────────────────────────
    def rd(f, off, n):
        f.seek(off)
        return f.read(n)

    src = open(a.iso or a.elf or a.bdump, 'rb')
    if org == 'bdump':
        def word(va):
            o = src_of_va(va)
            return struct.unpack('<I', data[o:o + 4])[0]
    else:
        def word(va):
            return struct.unpack('<I', rd(src, src_of_va(va), 4))[0]

    tab, gate_tab, geom_tab = [], [], []
    for (va, old, role, reach) in sites:
        got = word(va)
        assert got == old, ('VA 0x%08X 原字不符：盘上/ELF 0x%08X ≠ 声明 0x%08X'
                            % (va, got, old))
        new = (old & 0xFFFF0000) | SAFE
        tab.append(dict(va='0x%08X' % va, iso_off='0x%07X' % (va - ISO_OF_VA),
                        elf_off='0x%07X' % (va - ELF_OF_VA),
                        old_word='0x%08X' % old, new_word='0x%08X' % new,
                        old_imm='0x%04X' % (old & 0xFFFF), new_imm='0x%04X' % SAFE,
                        old_form=('零扩展（汉化 cave 形式）' if (old & 0xFFFF) < 0x8000
                                  else '符号扩展（原盘形式）'),
                        rt='$%d' % ((old >> 16) & 0x1F), role=role, reachability=reach))
    for (va, old, dis) in GATES:
        got = word(va)
        assert got == old, '闸门 0x%08X 原字不符：0x%08X ≠ 0x%08X' % (va, got, old)
        gate_tab.append(dict(va='0x%08X' % va, word='0x%08X' % got, dis=dis,
                             note='DBCS lead 区间上界（sltiu），不是相等比较 ⇒ 不动'))
    for (va, old, note) in K2_GEOM:
        geom_tab.append(dict(va='0x%08X' % va, word='0x%08X' % word(va), note=note))
    # 未被选中的排除项也要核对原字（证明它们「确实是那个形态」）
    exc_tab = []
    for (va, old, role, why) in EXCLUDED:
        got = word(va)
        exc_tab.append(dict(va='0x%08X' % va, word='0x%08X' % got,
                            matches_declared=(got == old), role=role, why=why,
                            in_patch=bool(a.all12)))
    rep['sites'] = tab
    rep['gates_untouched'] = gate_tab
    rep['k2_geometry'] = geom_tab
    rep['excluded_sites'] = exc_tab

    # ── 3) 写产物 ───────────────────────────────────────────────────────
    if org == 'bdump':
        buf = bytearray(data)
        for s in tab:
            o = src_of_va(int(s['va'], 16))
            buf[o:o + 4] = struct.pack('<I', int(s['new_word'], 16))
        tmp = a.out + '.tmp'
        open(tmp, 'wb').write(bytes(buf))
        shutil.move(tmp, a.out)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        if os.path.exists(a.out):
            os.remove(a.out)
        shutil.copyfile(a.iso or a.elf, a.out)
        with open(a.out, 'r+b') as f:
            for s in tab:
                f.seek(src_of_va(int(s['va'], 16)))
                f.write(struct.pack('<I', int(s['new_word'], 16)))
            f.flush()
            os.fsync(f.fileno())
    src.close()

    # ── 4) 回读 + 闸门未动 + 残留扫描 + 差异窗口 ─────────────────────────
    out = open(a.out, 'rb')

    def ord_(va):
        out.seek(src_of_va(va))
        return struct.unpack('<I', out.read(4))[0]

    readback = all(ord_(int(s['va'], 16)) == int(s['new_word'], 16) for s in tab)
    rep['readback_all_ok'] = readback
    assert readback, '回读不符'
    rep['gates_readback'] = ['0x%08X=0x%08X' % (va, ord_(va)) for (va, _o, _d) in GATES]
    assert all(ord_(va) == o for (va, o, _d) in GATES), '闸门被动了！'

    resid = {}
    kept = set()                       # 未打进补丁的排除项 VA（区间残留里容许的）
    for (va, _o, _r, _w) in EXCLUDED:
        if not a.all12:
            kept.add(va)
    resid_extra = []
    for (tag, lo, hi) in RESIDUAL:
        out.seek(src_of_va(lo))
        blob = out.read(hi - lo)
        hits = []
        for k in range(0, len(blob) - 3, 4):
            w = struct.unpack_from('<I', blob, k)[0]
            if (w & 0xFFFF) in (0x00B1, 0x00B5, 0xFFB1, 0xFFB5):
                va = lo + k
                hits.append('0x%08X:0x%08X' % (va, w))
                if va not in kept:
                    resid_extra.append('0x%08X:0x%08X' % (va, w))
        resid['%s [0x%X,0x%X)' % (tag, lo, hi)] = hits
    rep['in_range_imm_leftover'] = resid
    rep['in_range_imm_leftover_allowed'] = sorted('0x%08X' % v for v in kept)
    rep['in_range_imm_leftover_unexpected'] = resid_extra
    gates_now = [ord_(va) for (va, _o, _d) in GATES]
    out.close()

    runs = diff_runs(ref_path, a.out)
    total = sum(n for _o, n in runs)
    allowed = [(src_of_va(int(s['va'], 16)), 4) for s in tab]
    outside = [(o, n) for (o, n) in runs
               if not any(x <= o and o + n <= x + 4 for (x, _l) in allowed)]
    base_size = ref_size
    rep.update(out=os.path.relpath(a.out, ROOT), size=os.path.getsize(a.out),
               sha256=sha256_file(a.out), base_size=base_size,
               diff_runs=len(runs), diff_bytes=total, diff_runs_list=runs,
               diff_runs_outside_declared=len(outside), diff_runs_outside_list=outside,
               build_cmd=('python work\\builds\\GR_CSFIX\\tools\\csfix_apply.py %s %s --out %s%s'
                          % ('--elf' if mode == 'elf' else ('--iso' if mode == 'iso' else '--bdump'),
                             a.elf or a.iso or a.bdump, a.out,
                             ' --all12' if a.all12 else '')))
    rep['selfcheck'] = dict(
        size_unchanged=(os.path.getsize(a.out) == base_size),
        diff_only_in_declared_windows=(len(outside) == 0),
        diff_bytes_eq_2_per_site=(total == 2 * len(tab)),
        readback_all_ok=readback,
        gates_untouched_4=all(g == o for g, (va, o, _d) in zip(gates_now, GATES)),
        in_range_imm_leftover_only_declared=(not resid_extra))

    print('=' * 90)
    print('[csfix] mode=%s  基底=%s' % (mode, rep['base_check'].get('path')))
    print('        站点 %d 处：%s' % (len(tab), ', '.join(s['va'] for s in tab)))
    print('        sha256 = %s' % rep['sha256'])
    print('        size   = %d B（= 基底 %d B : %s）'
          % (rep['size'], base_size, '✓' if rep['selfcheck']['size_unchanged'] else '✗'))
    print('        diff   = %d run / %d B；声明窗口外 %d run %s'
          % (len(runs), total, len(outside), '✓' if not outside else '✗'))
    for k, v in resid.items():
        print('        区间残留 %-28s %d 处 %s' % (k, len(v), v if v else '✓'))
    for k, v in rep['selfcheck'].items():
        print('        自检 %-34s %s' % (k, '✓' if v else '✗'))
    print('        闸门回读 %s' % ' / '.join(rep['gates_readback']))
    mp = a.meta or (os.path.splitext(a.out)[0] + '.meta.json')
    with open(mp, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('[out] %s' % a.out)
    print('[out] %s' % mp)


if __name__ == '__main__':
    main()
