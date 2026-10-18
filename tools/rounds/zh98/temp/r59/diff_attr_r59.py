# -*- coding: utf-8 -*-
r"""round59 验收: 差异归属 (GR_ZH108 → 打了补丁的盘), 按**真实容器边界**算窗口。

口径沿用 work/builds/GR_ZH98/temp/r57/diff_attr_r57.py (ELF 区间按 PVD 实际文件长度 + ELF 头),
但允许区间收窄成**只有**: 字库像素容器 (COMMON.PAK 的 new_font_revised) + FONT.RES 槽 ——
本轮补丁只该动这两处, **不该**碰 PVD / 两个 IMG 条目表 / GR.IMG#551..565 / ELF / 文本容器。

用法: python diff_attr_r59.py <A.iso> <B.iso> [--json out.json]
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
from iso_tools import TAB_OFF, TAB_STEP                              # noqa: E402
import font_compact as FC                                            # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
SEC = 2048
CHUNK = 1 << 24


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
            if e['stored'] <= 0 or e['stored'] > 0x7FFFFFFF:
                continue
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
    print('字库像素容器: 0x%X..0x%X (%d B);  FONT.RES 槽: 0x%X..0x%X (%d B)'
          % (px0, px1, px1 - px0, ft0, ft1, ft1 - ft0))

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
            return 'ELF (LBA295) 内的短串区'
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

    elf_bytes = sum(n for (o, n) in raw if inside(o, n, (elf0, elf1)))
    pvd_bytes = sum(n for (o, n) in raw if inside(o, n, PVD))
    tab_bytes = sum(n for (o, n) in raw if any(inside(o, n, t) for t in tabs))
    n551_bytes = sum(n for (o, n) in raw if any(inside(o, n, r) for r in n551))
    pix_bytes = sum(n for (o, n) in raw if inside(o, n, (px0, px1)))
    ft_bytes = sum(n for (o, n) in raw if inside(o, n, (ft0, ft1)))
    allowed = pix_bytes + ft_bytes
    others = tot - allowed
    ok = (others == 0 and elf_bytes == 0 and pvd_bytes == 0 and tab_bytes == 0
          and n551_bytes == 0)
    print('')
    print('  字库像素容器内      : %d B' % pix_bytes)
    print('  FONT.RES 槽内       : %d B' % ft_bytes)
    print('  允许区间合计        : %d B' % allowed)
    print('  总差异              : %d B' % tot)
    print('  允许区间之外        : %d B  %s' % (others, '✓' if others == 0 else '✗'))
    print('  ELF (真实 %.1fMB)  : %d B  %s'
          % ((elf1 - elf0) / 1e6, elf_bytes, '✓' if elf_bytes == 0 else '✗'))
    print('  PVD (LBA16..17)     : %d B  %s' % (pvd_bytes, '✓' if pvd_bytes == 0 else '✗'))
    print('  两个 IMG 条目表      : %d B  %s' % (tab_bytes, '✓' if tab_bytes == 0 else '✗'))
    print('  GR.IMG#551..#565    : %d B  %s' % (n551_bytes, '✓' if n551_bytes == 0 else '✗'))
    print('  文本容器/其它条目    : %d B  %s'
          % (others, '✓' if others == 0 else '✗'))
    print('  ⇒ 总判: %s' % ('全绿 ✓' if ok else '有越界差异 ✗'))
    doc = dict(a=a.a, b=a.b, sha_a=tcslib.sha256_file(a.a), sha_b=tcslib.sha256_file(a.b),
               diff_bytes=tot, diff_spans=len(merged),
               pixel_container=[px0, px1], font_res_slot=[ft0, ft1], elf=[elf0, elf1],
               pixel_container_bytes=pix_bytes, font_res_bytes=ft_bytes,
               allowed_bytes=allowed, other_bytes=others, elf_bytes=elf_bytes,
               pvd_bytes=pvd_bytes, img_table_bytes=tab_bytes, gr_551_565_bytes=n551_bytes,
               ok=ok, by_container=dict((k, dict(bytes=v['bytes'], spans=v['spans']))
                                        for k, v in by.items()))
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main())
