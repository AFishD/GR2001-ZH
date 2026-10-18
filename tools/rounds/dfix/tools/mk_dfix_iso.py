# -*- coding: utf-8 -*-
r"""mk_dfix_iso.py —— 把 dfix_apply.py 的候选修复**打成可启动的整盘**（GR_DFIX 专用）。

为什么要这个脚本
----------------
`work\builds\GR_DISASM\tools\dfix_apply.py --iso X --out Y` 写出的是**抽出来的 ELF**
（37,453,732 B），不是 ISO —— 见该脚本 `read_elf_from_iso()` 与 `out = bytearray(data)`。
本脚本保留 dfix_apply.py 作为**唯一站点表真源**（import 它，不改它），
把 4 字节改动落在**整盘**的 `ELF_LBA*2048 + va2off(VA)` 处，于是产物可直接引导。

纪律
----
* 基底盘**只读**打开；写入只发生在 `--out` 指定的新文件（先整盘复制、再原地改字节）。
* 逐站点原字断言（复用 dfix_apply 的站点表与期望字）；不符者**跳过并报告**，`--strict` 则中止。
* 自证：尺寸不变 / 差异只落在声明窗口 / 每个窗口恰有预期新字 / 闸门与图集几何未被触碰 /
  从产物重新解析 ISO→ELF→站点回读。
* 逐字节 diff 以**流式**方式做（1 MiB 块），产出 `diff_runs`（连续差异段）。

用法
----
  python work\builds\GR_DFIX\tools\mk_dfix_iso.py `
    --base work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso `
    --out  work\builds\GR_DFIX\DFIX_pkt.iso --sets pkt --tag DFIX_pkt
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'GR_DISASM', 'tools')))
import dfix_apply as D  # noqa: E402  只读复用：站点表 + 血统 + VA 映射

SEC = 2048

# ── 每个修复集的"行为/风险"说明（写进 meta.json，逐站点复制） ──────────────
EFFECT = {
    'icon': (
        '把 DrawString 的图标特判比较值从 0x00B1/0x00B5 改成 0xFF00 ⇒ 该特判永不命中。'
        '命中时的行为：走 0x219C48..0x219C8C 的硬编码 UV 块 + 0x219CB8..0x219CF8 的硬编码字距'
        '(20.0f/11.0f)，并用 t0=1 调 AddOneWord ⇒ 写**副顶点包**（容量仅 2）⇒ 每 2 个图标字符'
        '强制一次主+副双包 flush + GIF 传输（帧率塌方），并每次踩 #1 的复位闸门。'
        '改动后这些字符改走**普通字形路径**（0x219C20 → 0x21ADE0）与普通字距。'),
    'icon-dead': (
        'CharWidth 原文残留，0 条外部入口（死代码）。改与不改在实机上不可观测；'
        '唯一作用是让盘上的同型常量一致，避免后续比对把"残留"误读成"活站点"。'),
    'icon-inert': (
        '惰性站点：该处是符号扩展的 0xFFFFFFB5 与 $a1=0x00B1 比较，恒不相等 ⇒ 走向不变。'
        '改动不改变任何行为，只为常量一致性。'),
    'fp': (
        'DrawString 拦截器结尾的返回目标从 0x00219A7C 提前到 0x00219A78，把被跳过的 '
        '`sq $fp,144(sp)` 补回来 ⇒ DrawString 尾声 `lq $fp,144(sp)` 恢复的是**正确的调用者 $fp**。'
        '静态上真受害者只有 0x2BA5C0 一处（把 $fp 当字体管理器再调 DrawString）。'),
    'pkt': (
        '把顶点包 flush 之后的"计数器复位"从**有条件**（fontmgr+0x48 != 0）改成**无条件**。'
        '原逻辑：count 在**写入并自增之后**才与容量（主包 1280 / 副包 2）比较；满则 flush，'
        '而 flush 后仅当 fontmgr+0x48 != 0 才把 count 归零 ⇒ 一旦在 count 已满时 +0x48 == 0，'
        '此后每次 AddOneWord 都把顶点写到下标 >= 容量 ⇒ 顶点缓冲越界写 ⇒ 相邻堆块头被改坏。'
        '改动后 count 每次 flush 必归零，写入下标重新有上界。'),
    'probe-slot': (
        '（探针）修 0x41708C/0x416FA0 处 mult 之后缺 mflo 的地址算式：字面读法下'
        ' slot = (lead-0xA1)+(trail-0xA1)+0xE0，与本工程登记的 slot=(lead-0xA1)*94+(trail-0xA1) 矛盾。'),
}
RISK = {
    'icon': (
        '只有在 0x00B1/0x00B5 本来就是**正常汉字**时才会显示变差（个别字变别的字/空白）；'
        '在 A 线它们本就是图标码。真正风险是"图标不再绘制"——若某文本把 0xB1/0xB5 当图标用，'
        '图标会消失（而不是画错），因为改后走普通字形路径。'),
    'icon-dead': '无（死代码）。',
    'icon-inert': '无（走向不变）。',
    'fp': (
        '若有调用者**故意**依赖"DrawString 之后 $fp 是垃圾"，补回 sq 会让它拿到不同的 $fp ⇒ '
        '文字错位/闪烁（与 ABI 相悖，几乎不可能）。预期与未修盘逐像素一致。'),
    'pkt': (
        '★ 本组是唯一可能改变**正常渲染语义**的一刀：flush 语义变化可能少送/多送一帧顶点，'
        '表现为渲染撕裂 / 丢字 / 闪烁。若出现，说明 fontmgr+0x48 == 0 时"故意不复位"是有意设计，'
        '必须立刻回滚本盘。因此本盘**必须单独测试**，不要与 icon/fp 混合。'),
    'probe-slot': '会改变**所有**对偶汉字的采样位置；只在探针盘上用，不进现役盘。',
}


def sha256_file(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(blk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def diff_runs(a, b, blk=1 << 20):
    """流式逐字节 diff，返回连续差异段 [(off, old_bytes, new_bytes)]。"""
    runs = []
    cur_off, cur_old, cur_new = None, bytearray(), bytearray()
    off = 0
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            ba, bb = fa.read(blk), fb.read(blk)
            if not ba and not bb:
                break
            if len(ba) != len(bb):
                raise SystemExit('尺寸不同，无法逐字节 diff')
            if ba != bb:
                for i in range(len(ba)):
                    if ba[i] != bb[i]:
                        if cur_off is None:
                            cur_off = off + i
                        cur_old.append(ba[i])
                        cur_new.append(bb[i])
                    elif cur_off is not None:
                        runs.append((cur_off, bytes(cur_old), bytes(cur_new)))
                        cur_off, cur_old, cur_new = None, bytearray(), bytearray()
            elif cur_off is not None:
                runs.append((cur_off, bytes(cur_old), bytes(cur_new)))
                cur_off, cur_old, cur_new = None, bytearray(), bytearray()
            off += len(ba)
    if cur_off is not None:
        runs.append((cur_off, bytes(cur_old), bytes(cur_new)))
    return runs


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='基底盘（只读）')
    ap.add_argument('--out', required=True, help='产物盘（必须不存在或是可覆盖的新文件）')
    ap.add_argument('--sets', required=True, help='dfix 修复集，用 + 连接：pkt / icon / fp / icon-dead / icon-inert')
    ap.add_argument('--all12', action='store_true', help='等于把 icon+icon-dead+icon-inert 一起算进 sets')
    ap.add_argument('--tag', default=None, help='meta.json 里的盘名标签')
    ap.add_argument('--meta', default=None, help='meta.json 路径（默认与 --out 同目录同名 .meta.json）')
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args()

    base = os.path.abspath(a.base)
    out = os.path.abspath(a.out)
    if base == out:
        raise SystemExit('--out 不能等于 --base')
    tag = a.tag or os.path.splitext(os.path.basename(out))[0]

    names = [x.strip() for x in a.sets.split('+') if x.strip()]
    if a.all12:
        names = ['icon', 'icon-dead', 'icon-inert'] + [n for n in names if n not in ('icon', 'icon-dead', 'icon-inert')]
    order, seen = [], set()
    for n in names:
        if n not in D.SETS:
            raise SystemExit('未知修复集 %r（可用 %s）' % (n, ', '.join(D.SETS)))
        if n not in seen:
            seen.add(n)
            order.append(n)

    # ── 读基底（只读） ──
    data, lba, elf_size = D.read_elf_from_iso(base)
    va2off, segs = D.va_map(data)
    line, gates, geom = D.lineage(data, va2off)
    base_iso_sha = sha256_file(base)
    base_size = os.path.getsize(base)

    print('=== mk_dfix_iso ===')
    print('基底   : %s' % base)
    print('  sha256 = %s  (%d B)' % (base_iso_sha, base_size))
    print('ELF    : @ LBA %d, %d B, sha256 = %s' % (lba, elf_size, hashlib.sha256(data).hexdigest()))
    print('血统   : %s' % line)
    print('闸门   : %s ; 图集几何 ncol=%d rowShift=%d V0=+%d V1=+%d' % (['0x%04X' % g for g in gates], *geom))
    print('修复集 : %s' % '+'.join(order))
    print()

    sites = []
    for n in order:
        for s in D.SETS[n]:
            sites.append((n,) + tuple(s))

    plan, skipped = [], []
    for (grp, va, name, exp, new) in sites:
        fo = va2off(va)
        cur = struct.unpack_from('<I', data, fo)[0]
        iso_off = lba * SEC + fo
        rec = dict(group=grp, va='0x%08X' % va, iso_off=iso_off, iso_off_hex='0x%08X' % iso_off,
                   elf_off=fo, orig='%08X' % cur, expect='%08X' % exp, new='%08X' % new,
                   name=name, effect=EFFECT.get(grp, ''), risk=RISK.get(grp, ''))
        if cur == exp:
            plan.append(rec)
        else:
            rec['skipped'] = '原字不符'
            skipped.append(rec)
    print('--- 站点断言（%d / %d 可打） ---' % (len(plan), len(sites)))
    for r in plan:
        print('  OK [%s] VA %s ISO %s  %s -> %s  %s' % (r['group'], r['va'], r['iso_off_hex'],
                                                        r['orig'], r['new'], r['name']))
    for r in skipped:
        print('  !! [%s] VA %s 期望 %s 实得 %s  %s' % (r['group'], r['va'], r['expect'], r['orig'], r['name']))
    if skipped and a.strict:
        raise SystemExit('--strict：存在原字不符站点，中止')

    # ── 复制 + 打字节 ──
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        print('\n[注意] 产物已存在，将被整盘覆盖：%s' % out)
    shutil.copyfile(base, out)
    with open(out, 'r+b') as f:
        for r in plan:
            f.seek(r['iso_off'])
            f.write(struct.pack('<I', int(r['new'], 16)))
        f.flush()
        os.fsync(f.fileno())
    print('\n[写出] %s' % out)

    # ── 自证 1: 尺寸 / 逐字节 diff ──
    out_size = os.path.getsize(out)
    runs = diff_runs(base, out)
    windows = [(r['iso_off'], r['iso_off'] + 4) for r in plan]
    inwin = all(any(lo <= o and o + len(ob) <= hi for (lo, hi) in windows) for (o, ob, _nb) in runs)
    nbytes = sum(len(ob) for (_o, ob, _nb) in runs)
    touched = sum(1 for (lo, hi) in windows if any(lo <= o < hi for (o, _ob, _nb) in runs))
    print('自证 size_unchanged       %s (%d B)' % ('OK' if out_size == base_size else 'FAIL', out_size))
    print('自证 diff_only_in_windows %s (差异 %d 段 / %d 字节)' % ('OK' if inwin else 'FAIL', len(runs), nbytes))
    print('自证 每个窗口都真有改动    %s (%d / %d)' % ('OK' if touched == len(plan) else 'FAIL', touched, len(plan)))

    # ── 自证 2: 从产物重新解析 ISO → ELF → 站点回读 ──
    d2, lba2, size2 = D.read_elf_from_iso(out)
    va2off2, _ = D.va_map(d2)
    rb_ok = True
    for r in plan:
        got = struct.unpack_from('<I', d2, va2off2(int(r['va'], 16)))[0]
        if got != int(r['new'], 16):
            rb_ok = False
            print('  回读不符 VA %s: %08X' % (r['va'], got))
    ro_ok = all(struct.unpack_from('<I', d2, va2off2(va))[0] == struct.unpack_from('<I', data, va2off(va))[0]
                for (va, _n) in D.GATES + D.ATLAS_GEOM)
    print('自证 readback_all_ok      %s' % ('OK' if rb_ok else 'FAIL'))
    print('自证 闸门/图集几何未触碰   %s' % ('OK' if ro_ok else 'FAIL'))
    print('自证 产物 LBA/size 不变    %s (LBA %d, %d B)' % ('OK' if (lba2 == lba and size2 == elf_size) else 'FAIL', lba2, size2))

    out_sha = sha256_file(out)
    print('\n产物 sha256 = %s' % out_sha)

    meta = dict(
        tag=tag, out_dir=os.path.dirname(out), out_file=os.path.basename(out),
        sets=order, sets_expr='+'.join(order),
        base_file=base, base_sha256=base_iso_sha, base_bytes=base_size,
        base_elf_sha256=hashlib.sha256(data).hexdigest(),
        base_elf_lba=lba, base_elf_bytes=elf_size,
        lineage=line, gates=['0x%04X' % g for g in gates],
        atlas_geom=dict(ncol=geom[0], row_shift=geom[1], v0=geom[2], v1=geom[3]),
        site_count=len(plan), sites_skipped=skipped, sites=plan,
        iso_offsets=[r['iso_off_hex'] for r in plan],
        diff_runs=[dict(iso_off='0x%08X' % o, len=len(ob), old=ob.hex(), new=nb.hex())
                   for (o, ob, nb) in runs],
        diff_run_count=len(runs), diff_bytes=nbytes,
        sha256=out_sha, bytes=out_size,
        selfcheck=dict(size_unchanged=out_size == base_size,
                       diff_only_in_windows=inwin,
                       every_window_touched=touched == len(plan),
                       readback_all_ok=rb_ok,
                       gates_geom_untouched=ro_ok,
                       elf_lba_size_unchanged=(lba2 == lba and size2 == elf_size)),
        check_cmd='python work\\builds\\GR_DISASM\\tools\\dfix_apply.py --iso %s --check' % out,
        check_output_file=os.path.join(os.path.dirname(HERE), 'audit', 'check_%s.txt' % tag),
        built_by='GR_DFIX 执行者 / mk_dfix_iso.py',
    )
    meta_path = a.meta or (os.path.splitext(out)[0] + '.meta.json')
    with open(meta_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print('meta   : %s' % meta_path)
    return 0 if (inwin and rb_ok and ro_ok and out_size == base_size) else 1


if __name__ == '__main__':
    sys.exit(main())
