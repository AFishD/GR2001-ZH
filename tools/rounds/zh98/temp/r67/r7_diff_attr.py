# -*- coding: utf-8 -*-
r"""r7_diff_attr.py — round67 验收: **差异归属** (按真实容器边界算窗口)。

基于 `work/builds/GR_ZH98/temp/r57/diff_attr_r57.py` (它已修正 round56 的"ELF 窗口过小"假绿),
本轮再加两条更强的断言:

  · `FONT.RES` 槽内差异必须 = 0 (本轮 FT 记录表一个字节都不该动 —— 对偶码索引 ≥224=nrec
    ⇒ 永远不走记录表);
  · 全部差异字节必须落在 **329 个新字格的字节偏移集合**内 (比"落在像素容器内"更强)。

用法: python r7_diff_attr.py <A.iso> <B.iso> [--json out.json]
"""
import argparse
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
import dump_font as DF                                               # noqa: E402
from iso_tools import TAB_OFF, TAB_STEP                              # noqa: E402
import font_compact as FC                                            # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
SEC = 2048
CHUNK = 1 << 24
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
SLOT_LO, N_NEW = 1175, 329


def diff_ranges(pa, pb):
    sa, sb = os.path.getsize(pa), os.path.getsize(pb)
    assert sa == sb, '尺寸不同: %d vs %d' % (sa, sb)
    out = []
    with open(pa, 'rb') as fa, open(pb, 'rb') as fb:
        off = 0
        while off < sa:
            n = min(CHUNK, sa - off)
            ba, bb = fa.read(n), fb.read(n)
            if ba == bb:
                off += n
                continue
            i = 0
            while i < n:
                if ba[i] == bb[i]:
                    i += 1
                    continue
                j = i
                while j < n and ba[j] != bb[j]:
                    j += 1
                out.append((off + i, j - i))
                i = j
            off += n
    return out


def merge(rngs, gap=64):
    out = []
    for (o, n) in sorted(rngs):
        if out and o - (out[-1][0] + out[-1][1]) <= gap:
            e = max(out[-1][0] + out[-1][1], o + n)
            out[-1] = (out[-1][0], e - out[-1][0])
        else:
            out.append((o, n))
    return out


def elf_range(iso):
    base = FC.find_elf_base(iso)
    hdr = bytes(iso.mm[base:base + 64])
    e_shoff = struct.unpack_from('<I', hdr, 0x20)[0]
    e_shentsize, e_shnum = struct.unpack_from('<HH', hdr, 0x2E)
    return base, base + e_shoff + e_shentsize * e_shnum


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--json', default=None)
    ap.add_argument('--gap', type=int, default=64)
    a = ap.parse_args()

    iso_a, iso_b = tcslib.Iso(a.a), tcslib.Iso(a.b)
    print('A = %s  (sha %s)' % (os.path.basename(a.a), tcslib.sha256_file(a.a)[:16]))
    print('B = %s  (sha %s)' % (os.path.basename(a.b), tcslib.sha256_file(a.b)[:16]))

    regions = []
    for tag, lba in (('MENU.IMG', MENU_LBA), ('GR.IMG', GR_LBA)):
        n = FC.img_entry_count(iso_a, lba)
        for idx in range(n):
            e = iso_a.img_entry(lba, idx)
            if 0 < e['stored'] <= 0x7FFFFFFF:
                regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                                '%s#%d %s' % (tag, idx, e['name'])))
    regions.sort()
    f = DF.load_font(a.a)
    px0 = f['pak_e']['iso_off'] + f['atlas']['px_off']
    px1 = px0 + f['atlas']['px_size']
    ft0 = f['ft_e']['iso_off']
    ft1 = ft0 + f['ft_e']['stored']
    tabs = [(MENU_LBA * SEC + TAB_OFF,
             MENU_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, MENU_LBA)),
            (GR_LBA * SEC + TAB_OFF,
             GR_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, GR_LBA))]
    elf0, elf1 = elf_range(iso_a)
    PVD = (16 * SEC, 18 * SEC)
    n551 = []
    for idx in range(551, 566):
        e = iso_a.img_entry(GR_LBA, idx)
        if 0 < e['stored'] < 0x7FFFFFFF:
            n551.append((e['iso_off'], e['iso_off'] + e['stored'],
                         'GR.IMG#%d %s' % (idx, e['name'])))
    iso_a.close()
    iso_b.close()
    print('ELF 区间 (按 ELF 头): 0x%X..0x%X (%.1f MB)' % (elf0, elf1, (elf1 - elf0) / 1e6))

    # ★ 329 个新字格覆盖到的字节偏移 (绝对 ISO 偏移)
    segs = tcslib.atlas_container_segments(
        bytes(f['atlas']['pak'][f['atlas']['px_off']:
                                f['atlas']['px_off'] + f['atlas']['px_size']]), 1024 // 2)
    assert segs, '认不出封包分段'

    def off_of(x, y):
        k = y // tcslib.ATLAS_SEG_ROWS
        first_row, doff, nbytes = segs[k]
        rel = (y - first_row) * (1024 // 2) + x // 2
        assert 0 <= rel < nbytes, (x, y)
        return px0 + doff + rel
    cell_bytes = set()
    for slot in range(SLOT_LO, SLOT_LO + N_NEW):
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        for dy in range(CH):
            for dx in range(0, CW, 2):
                cell_bytes.add(off_of(x + dx, y + dy))
    print('★ 329 个新字格的字节集合: %d B (绝对 0x%X..0x%X)'
          % (len(cell_bytes), min(cell_bytes), max(cell_bytes)))

    raw = diff_ranges(a.a, a.b)
    merged = merge(raw, gap=a.gap)
    tot = sum(n for _o, n in raw)
    print('差异: %d 个字节, 聚成 %d 段 (并段间隔 %d B)' % (tot, len(merged), a.gap))

    def owner(o, n):
        e = o + n
        if o >= px0 and e <= px1:
            return '★字库像素容器'
        if o >= ft0 and e <= ft1:
            return 'FONT.RES 槽'
        if o >= elf0 and e <= elf1:
            return 'ELF (LBA295)'
        for (s, t, nm) in regions:
            if o >= s and e <= t:
                return nm
        return '(未归属)'

    by, by_exact = {}, {}
    for (o, n) in merged:
        k = owner(o, n)
        d = by.setdefault(k, dict(bytes=0, spans=0, first=o, last=o + n))
        d['spans'] += 1
        d['first'] = min(d['first'], o)
        d['last'] = max(d['last'], o + n)
    for (o, n) in raw:
        k = owner(o, n)
        by_exact[k] = by_exact.get(k, 0) + n
    for k in by:
        by[k]['bytes'] = by_exact.get(k, 0)
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]['bytes']):
        print('   %-46s %9d B / %4d 段   [0x%X..0x%X]'
              % (k, v['bytes'], v['spans'], v['first'], v['last']))

    def inside(o, n, reg):
        return o >= reg[0] and o + n <= reg[1]

    elf_hits = [(o, n) for (o, n) in raw if inside(o, n, (elf0, elf1))]
    elf_bytes = sum(n for _o, n in elf_hits)
    pvd_bytes = sum(n for (o, n) in raw if inside(o, n, PVD))
    tab_bytes = sum(n for (o, n) in raw if any(inside(o, n, t) for t in tabs))
    n551_bytes = sum(n for (o, n) in raw if any(inside(o, n, r) for r in n551))
    pix_bytes = sum(n for (o, n) in raw if inside(o, n, (px0, px1)))
    ft_bytes = sum(n for (o, n) in raw if inside(o, n, (ft0, ft1)))
    in_cells = sum(n for (o, n) in raw if all(i in cell_bytes for i in range(o, o + n)))
    outside_all = tot - pix_bytes

    ok = dict(pvd=pvd_bytes == 0, img_tabs=tab_bytes == 0, gr551_565=n551_bytes == 0,
              elf=elf_bytes == 0, font_res=ft_bytes == 0, outside_pixel=outside_all == 0,
              in_new_cells=in_cells == tot)
    print('')
    print('  字库像素容器内            : %d B' % pix_bytes)
    print('  其中落在 **329 个新字格**内: %d B / %d  %s'
          % (in_cells, tot, '✓' if ok['in_new_cells'] else '✗'))
    print('  FONT.RES 槽内             : %d B  %s' % (ft_bytes, '✓' if ok['font_res'] else '✗'))
    print('  像素容器之外的全部差异     : %d B  %s'
          % (outside_all, '✓' if ok['outside_pixel'] else '✗'))
    print('  PVD (LBA16..17)           : %d B  %s' % (pvd_bytes, '✓' if ok['pvd'] else '✗'))
    print('  两个 IMG 条目表            : %d B  %s'
          % (tab_bytes, '✓' if ok['img_tabs'] else '✗'))
    print('  GR.IMG#551..#565          : %d B  %s'
          % (n551_bytes, '✓' if ok['gr551_565'] else '✗'))
    print('  ELF (真实 37.5MB)         : %d B  %s' % (elf_bytes, '✓' if ok['elf'] else '✗'))
    print('  总差异                    : %d B' % tot)
    print('  ⇒ %s' % ('全部断言 PASS ✓' if all(ok.values()) else '★有断言不过: %s'
                        % [k for k, v in ok.items() if not v]))
    doc = dict(a=a.a, b=a.b, sha_a=tcslib.sha256_file(a.a), sha_b=tcslib.sha256_file(a.b),
               diff_bytes=tot, diff_spans=len(merged), elf=(elf0, elf1),
               pvd_bytes=pvd_bytes, img_table_bytes=tab_bytes, gr_551_565_bytes=n551_bytes,
               pixel_container_bytes=pix_bytes, in_new_cells_bytes=in_cells,
               font_res_bytes=ft_bytes, outside_pixel_bytes=outside_all, checks=ok,
               by_container=dict((k, dict(bytes=v['bytes'], spans=v['spans']))
                                 for k, v in by.items()))
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0 if all(ok.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
