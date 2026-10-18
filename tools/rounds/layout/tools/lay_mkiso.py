# -*- coding: utf-8 -*-
r"""lay_mkiso.py —— 【GR_LAYOUT】把逐站点单变量改动落成**可引导整盘**（基底只读）。

用法
----
  python lay_mkiso.py --base <基底.iso> --out <产物.iso> --set <名字> [--set ...] [--tag T]

纪律
----
* 基底**只读**（'rb'）；产物先整盘复制再原地改字节。
* 逐站点**原字断言**：不符即中止（--no-strict 可降级为跳过并报告）。
* 自证：尺寸不变 / 逐字节 diff 只落在声明窗口 / 每窗口恰有改动 / 产物回读 /
  闸门与图集几何 8 个字节**必须**与基底逐字节相同 / 门控无关区未被触碰。
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

# ───────────────────────── 站点集（全部为 K2/B 线上的**现值** → 新值） ─────────────────────────
SETS = {
    # I2：StringWidth 的"等宽字体早退"用**字节长度**，而同函数的汉化主循环已改成**字形数**。
    #     把该早退关掉（无条件走 0x21AC54 起的字形口径循环）⇒ 两套口径合一。
    'strwidth_mono': [
        (0x0021AC40, 0x10400004, 0x10000004,
         'StringWidth: beq $v0,$zero,+4 → beq $zero,$zero,+4（关掉"字节长度×固定宽"早退；'
         '原分支的判据是 [font+0x24]!=0，且乘数 s0 是字节长度）'),
    ],
    # I3：AddOneWord 的 4 条 flush 路径把 GIF 发送参数 a1 由原盘 1 改成 0。
    'sendmode': [
        (0x00219FF4, 0x24050000, 0x24050001, '主包 flush: jal 0x519AC0 的 a1 0→1（恢复原盘）'),
        (0x0021A0F8, 0x24050000, 0x24050001, '副包 flush: jal 0x519AC0 的 a1 0→1（恢复原盘）'),
        (0x0021A1C4, 0x24050000, 0x24050001, 'flush 路径三: a1 0→1（恢复原盘）'),
        (0x0021A2C4, 0x24050000, 0x24050001, 'flush 路径四: a1 0→1（恢复原盘）'),
    ],
    # I3b：GIF 传输函数里的模式比较被 NOP 掉（与 sendmode 同区，单独一盘便于二分）。
    'gifbranch': [
        (0x00519AC8, 0x00000000, 0x10C30054,
         '0x519AC0 内 beq $a2,$v1,+84 被 NOP ⇒ 恢复（与 a1 参数是一对，分盘二分）'),
    ],
    # I4：排版里 GetStringWidth 的 "+1" 被删（1 px/串漂移）。
    'layout_plus1': [
        (0x0021CECC, 0x00000000, 0x24420001, 'RSUIText 排版: v0 = 宽度 + 1（恢复原盘的 +1）'),
    ],
}

# 只读参照：这些地址**必须**在产物里与基底逐字节相同
REF_GATES = [0x00416EE8, 0x00417160, 0x0041751C, 0x005656A4]
REF_GEOM = [0x004170AC, 0x004170E8, 0x004170F8, 0x004170FC]
# 汉化"槽位/步进"核心站点（自证：本补丁一律不碰）
REF_CORE = [0x00416F9C, 0x00416FA0, 0x00416FA4, 0x00416FA8,
            0x00417088, 0x0041708C, 0x00417090, 0x00417094]


def sha256_file(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(blk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def iso_find_elf(f):
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

    def va2off(va):
        for (v, o, s) in segs:
            if v <= va < v + s:
                return o + (va - v)
        raise SystemExit('VA 0x%08X 不在 PT_LOAD 内' % va)
    return va2off, segs


def diff_runs(a, b, blk=1 << 20):
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
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--set', dest='sets', action='append', required=True)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--meta', default=None)
    ap.add_argument('--no-strict', action='store_true')
    a = ap.parse_args()
    base, out = os.path.abspath(a.base), os.path.abspath(a.out)
    if base == out:
        raise SystemExit('--out 不能等于 --base')
    tag = a.tag or os.path.splitext(os.path.basename(out))[0]

    sites = []
    for n in a.sets:
        if n not in SETS:
            raise SystemExit('未知 --set %r（可用 %s）' % (n, ', '.join(SETS)))
        for s in SETS[n]:
            sites.append((n,) + tuple(s))

    data, lba, elf_size = read_elf_from_iso(base)
    va2off, segs = va_map(data)
    base_sha = sha256_file(base)
    base_size = os.path.getsize(base)
    print('=== lay_mkiso ===')
    print('基底   : %s' % base)
    print('  sha256 = %s (%d B)' % (base_sha, base_size))
    print('ELF    : @LBA %d, %d B, sha256 = %s' % (lba, elf_size, hashlib.sha256(data).hexdigest()))
    print('PT_LOAD: %s' % [(hex(v), hex(o), hex(s)) for (v, o, s) in segs])
    print('装载点 : COLS=%d SKIP=%d Y0=%d V1=%d GATE=%s'
          % (struct.unpack_from('<I', data, va2off(0x4170AC))[0] & 0xFFFF,
             struct.unpack_from('<I', data, va2off(0x4170E8))[0] & 0xFFFF,
             struct.unpack_from('<I', data, va2off(0x4170F8))[0] & 0xFFFF,
             struct.unpack_from('<I', data, va2off(0x4170FC))[0] & 0xFFFF,
             ['0x%04X' % (struct.unpack_from('<I', data, va2off(g))[0] & 0xFFFF)
              for g in REF_GATES]))

    plan, skipped = [], []
    for (grp, va, exp, new, note) in sites:
        fo = va2off(va)
        cur = struct.unpack_from('<I', data, fo)[0]
        rec = dict(group=grp, va='0x%08X' % va, iso_off=lba * SEC + fo,
                   iso_off_hex='0x%08X' % (lba * SEC + fo), elf_off=fo,
                   now='%08X' % cur, expect='%08X' % exp, new='%08X' % new, note=note)
        if cur == exp:
            plan.append(rec)
        else:
            rec['skipped'] = '原字不符'
            skipped.append(rec)
        print('  %s [%s] VA %s ISO %s  %08X -> %08X  %s'
              % ('OK ' if cur == exp else '!! ', grp, rec['va'], rec['iso_off_hex'],
                 cur, new, note))
    if skipped and not a.no_strict:
        raise SystemExit('存在原字不符站点，中止（--no-strict 可跳过）')

    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        for r in plan:
            f.seek(r['iso_off'])
            f.write(struct.pack('<I', int(r['new'], 16)))
        f.flush()
        os.fsync(f.fileno())
    print('\n[写出] %s' % out)

    out_size = os.path.getsize(out)
    runs = diff_runs(base, out)
    win = [(r['iso_off'], r['iso_off'] + 4) for r in plan]
    inwin = all(any(lo <= o and o + len(ob) <= hi for (lo, hi) in win) for (o, ob, _n) in runs)
    nbytes = sum(len(ob) for (_o, ob, _n) in runs)
    touched = sum(1 for (lo, hi) in win if any(lo <= o < hi for (o, _ob, _n) in runs))
    print('自证 size_unchanged        %s (%d B)' % ('OK' if out_size == base_size else 'FAIL', out_size))
    print('自证 diff_only_in_windows  %s (差异 %d 段 / %d 字节)' % ('OK' if inwin else 'FAIL', len(runs), nbytes))
    print('自证 every_window_touched  %s (%d/%d)' % ('OK' if touched == len(plan) else 'FAIL', touched, len(plan)))

    d2, lba2, size2 = read_elf_from_iso(out)
    v2, _ = va_map(d2)
    rb = all(struct.unpack_from('<I', d2, v2(int(r['va'], 16)))[0] == int(r['new'], 16) for r in plan)
    ro = all(struct.unpack_from('<I', d2, v2(x))[0] == struct.unpack_from('<I', data, va2off(x))[0]
             for x in REF_GATES + REF_GEOM + REF_CORE)
    print('自证 readback_all_ok       %s' % ('OK' if rb else 'FAIL'))
    print('自证 gates/geom/core 未动   %s (%d 处)' % ('OK' if ro else 'FAIL',
                                                   len(REF_GATES + REF_GEOM + REF_CORE)))
    print('自证 产物 ELF sha256       %s' % hashlib.sha256(d2).hexdigest())
    out_sha = sha256_file(out)
    print('\n产物 sha256 = %s' % out_sha)

    meta = dict(tag=tag, out_dir=os.path.dirname(out), out_file=os.path.basename(out),
                base_file=base, base_sha256=base_sha, base_bytes=base_size,
                base_elf_sha256=hashlib.sha256(data).hexdigest(), base_elf_lba=lba,
                base_elf_bytes=elf_size, sets=a.sets, site_count=len(plan),
                sites_skipped=skipped, sites=plan,
                iso_offsets=[r['iso_off_hex'] for r in plan],
                diff_runs=[dict(iso_off='0x%08X' % o, len=len(ob), old=ob.hex(), new=nb.hex())
                           for (o, ob, nb) in runs],
                diff_run_count=len(runs), diff_bytes=nbytes,
                sha256=out_sha, bytes=out_size,
                out_elf_sha256=hashlib.sha256(d2).hexdigest(),
                readback_refs=[dict(va='0x%08X' % x,
                                    word='%08X' % struct.unpack_from('<I', d2, v2(x))[0])
                               for x in REF_GATES + REF_GEOM + REF_CORE],
                selfcheck=dict(size_unchanged=out_size == base_size,
                               diff_only_in_windows=inwin,
                               every_window_touched=touched == len(plan),
                               readback_all_ok=rb, gates_geom_core_untouched=ro,
                               elf_lba_size_unchanged=(lba2 == lba and size2 == elf_size)),
                built_by='GR_LAYOUT 执行者 / lay_mkiso.py')
    meta_path = a.meta or (os.path.splitext(out)[0] + '.meta.json')
    with open(meta_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print('meta   : %s' % meta_path)
    return 0 if (inwin and rb and ro and out_size == base_size and touched == len(plan)) else 1


if __name__ == '__main__':
    sys.exit(main())
