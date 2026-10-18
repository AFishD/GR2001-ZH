# -*- coding: utf-8 -*-
r"""round56 验收 A: GR_ZH106 vs GR_ZH105 的**差异归属** (只读)。

判据 (用户给的验收条件):
  · 差异**只**允许落在: ① 字库像素容器 ② FONT.RES ③ SFXML 所在条目 (MENU.IMG#283)
                         ④ 文本容器 (MENU.IMG#25 / GR.IMG#902)
  · ELF / PVD / 两个 IMG 的**条目表** / 制作组名单 GR.IMG#551..#565 差异必须 **0**。

用法: python diff_attr.py <A.iso> <B.iso> [--json out.json]
"""
import argparse
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
import dump_font as DF                                               # noqa: E402
from iso_tools import TAB_OFF, TAB_STEP                             # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_compact as FC                                            # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
SEC = 2048
CHUNK = 1 << 24


def diff_ranges(pa, pb):
    """逐块比对两个 ISO, 返回 [(off, nbytes)] (只读)。"""
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
            # 逐字节找差异并聚成区间
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
    """把相邻 (间隔 ≤gap) 的差异区间并成一段, 便于按容器归属。"""
    out = []
    for (o, n) in sorted(rngs):
        if out and o - (out[-1][0] + out[-1][1]) <= gap:
            e = max(out[-1][0] + out[-1][1], o + n)
            out[-1] = (out[-1][0], e - out[-1][0])
        else:
            out.append((o, n))
    return out


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

    # 容器区间表 (两个 IMG 全量, 用名字表定条目数)
    regions = []
    for tag, lba in (('MENU.IMG', MENU_LBA), ('GR.IMG', GR_LBA)):
        n = FC.img_entry_count(iso_a, lba)
        for idx in range(n):
            e = iso_a.img_entry(lba, idx)
            if e['stored'] <= 0 or e['stored'] > 0x7FFFFFFF:
                continue
            regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                            '%s#%d %s' % (tag, idx, e['name'])))
    regions.sort()
    # 字库像素容器
    f = DF.load_font(a.a)
    px0 = f['pak_e']['iso_off'] + f['atlas']['px_off']
    px1 = px0 + f['atlas']['px_size']
    ft0 = f['ft_e']['iso_off']
    ft1 = ft0 + f['ft_e']['stored']
    # IMG 条目表区间
    tabs = [(MENU_LBA * SEC + TAB_OFF, MENU_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, MENU_LBA)),
            (GR_LBA * SEC + TAB_OFF, GR_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, GR_LBA))]
    # ELF / PVD
    ELF = (295 * SEC, 295 * SEC + 0x180000)
    PVD = (16 * SEC, 18 * SEC)
    names_551_565 = []
    for idx in range(551, 566):
        e = iso_a.img_entry(GR_LBA, idx)
        if e['stored'] > 0 and e['stored'] < 0x7FFFFFFF:
            names_551_565.append((e['iso_off'], e['iso_off'] + e['stored'], 'GR.IMG#%d %s'
                                  % (idx, e['name'])))
    iso_a.close(); iso_b.close()

    raw = diff_ranges(a.a, a.b)
    merged = merge(raw, gap=a.gap)
    tot = sum(n for _o, n in raw)
    print('差异: %d 个字节, 聚成 %d 段 (并段间隔 %d B)' % (tot, len(merged), a.gap))

    def owner(o, n):
        e = o + n
        if o >= px0 and e <= px1:
            return '★字库像素容器 (COMMON.PAK new_font_revised)'
        if o >= ft0 and e <= ft1:
            return 'FONT.RES 槽'
        for (s, t, nm) in regions:
            if o >= s and e <= t:
                return nm
        return '(未归属)'

    by = {}
    for (o, n) in merged:
        k = owner(o, n)
        d = by.setdefault(k, dict(bytes=0, spans=0, first=o, last=o + n))
        d['spans'] += 1
        d['first'] = min(d['first'], o); d['last'] = max(d['last'], o + n)
    # ★ 字节数按**原始差异区间**统计 (并段只用来给"首..末"范围), 否则会把中间的相同字节算进去
    by_exact = {}
    for (o, n) in raw:
        k = owner(o, n)
        by_exact[k] = by_exact.get(k, 0) + n
    for k in by:
        by[k]['bytes'] = by_exact.get(k, 0)
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]['bytes']):
        print('   %-46s %9d B / %4d 段   [%d..%d]' % (k, v['bytes'], v['spans'],
                                                      v['first'], v['last']))

    def in_region(o, n, reg):
        return o >= reg[0] and o + n <= reg[1]

    elf_bytes = sum(n for (o, n) in raw if in_region(o, n, ELF))
    pvd_bytes = sum(n for (o, n) in raw if in_region(o, n, PVD))
    tab_bytes = 0
    for (o, n) in raw:
        for (s, t) in tabs:
            if o >= s and o + n <= t:
                tab_bytes += n
    n551 = sum(n for (o, n) in raw if any(in_region(o, n, r) for r in names_551_565))
    pix_bytes = sum(n for (o, n) in raw if in_region(o, n, (px0, px1)))
    ft_bytes = sum(n for (o, n) in raw if in_region(o, n, (ft0, ft1)))
    allowed = pix_bytes + ft_bytes
    for lbl in ('MENU.IMG#25 ', 'MENU.IMG#283 ', 'GR.IMG#902 '):
        for k, v in by.items():
            if k.startswith(lbl):
                allowed += v['bytes']
    others = tot - allowed
    doc = dict(a=a.a, b=a.b, sha_a=tcslib.sha256_file(a.a), sha_b=tcslib.sha256_file(a.b),
               diff_bytes=tot, diff_spans=len(merged),
               by_container=dict((k, dict(bytes=v['bytes'], spans=v['spans'])) for k, v in by.items()),
               elf_bytes=elf_bytes, pvd_bytes=pvd_bytes, img_table_bytes=tab_bytes,
               gr_551_565_bytes=n551, pixel_container_bytes=pix_bytes, font_res_bytes=ft_bytes,
               allowed_bytes=allowed, other_bytes=others,
               note='允许落在: 字库像素容器 + FONT.RES + SFXML(MENU#283) + 文本容器(MENU#25/GR#902)')
    print('')
    print('  字库像素容器内      : %d B' % pix_bytes)
    print('  FONT.RES 槽内       : %d B' % ft_bytes)
    print('  允许区间合计        : %d B' % allowed)
    print('  总差异              : %d B' % tot)
    print('  允许区间之外        : %d B  %s' % (others, '✓' if others == 0 else '✗'))
    print('  ELF (LBA295)        : %d B  %s' % (elf_bytes, '✓' if elf_bytes == 0 else '✗'))
    print('  PVD (LBA16..17)     : %d B  %s' % (pvd_bytes, '✓' if pvd_bytes == 0 else '✗'))
    print('  两个 IMG 条目表      : %d B  %s' % (tab_bytes, '✓' if tab_bytes == 0 else '✗'))
    print('  GR.IMG#551..#565    : %d B  %s' % (n551, '✓' if n551 == 0 else '✗'))
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
