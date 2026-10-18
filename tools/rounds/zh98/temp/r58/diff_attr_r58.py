# -*- coding: utf-8 -*-
r"""round58 验收: 差异归属 (GR_ZH107 → GR_ZH108 "容器级重编码覆盖面补全")。

与 r57 版的差别: **允许区间按"容器级文本登记表"算** (名字/模式匹配, 不写死索引)
  = 登记容器里本轮真的动了字节的那些 + 注入器每轮重写的 3 个可注入容器 + 字库像素容器 +
    FONT.RES 槽; 其余一律判 ✗。
用法: python diff_attr_r58.py <A.iso> <B.iso> [--json out.json] [--expect-elf-short ...]
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
import font_compact as FC                                            # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
SEC = 2048
CHUNK = 1 << 24
RE_MATCH = __import__('re').compile(r'^(MENU\.IMG|GR\.IMG)#\d+ ')


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
    """按 ELF 头 (e_shoff + e_shentsize*e_shnum) 取 ELF 区间 —— 不再用拍脑袋的 0x180000。"""
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
    ap.add_argument('--expect-elf-short', default='',
                    help='期望 ELF 内唯一差异的短串起始偏移 (逗号分隔), 用于逐段核对')
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
    print('ELF 区间 (按 ELF 头): 0x%X..0x%X (%.1f MB)   [round56 用的是 0x%X..0x%X (%.2f MB)]'
          % (elf0, elf1, (elf1 - elf0) / 1e6, 295 * SEC, 295 * SEC + 0x180000, 0x180000 / 1e6))

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

    by = {}
    by_exact = {}
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
    allowed = pix_bytes + ft_bytes
    allowed_containers = {}
    for k, v in by.items():
        # by 的键形如 'MENU.IMG#26 DE_STRINGS.RES' (或 '(未归属)' 等)
        m = RE_MATCH.match(k)
        if not m:
            continue
        name = k.split(' ', 1)[1] if ' ' in k else ''
        if FC.registry_match(name) or k.startswith(('MENU.IMG#25 ', 'MENU.IMG#283 ',
                                                    'GR.IMG#902 ')):
            allowed += v['bytes']
            allowed_containers[k] = v['bytes']
    others = tot - allowed - elf_bytes
    exp = []
    for x in a.expect_elf_short.split(','):
        x = x.strip()
        if not x:
            continue
        if ':' in x:
            o, l = x.split(':')
            exp.append((int(o, 0), int(l, 0)))
        else:
            exp.append((int(x, 0), 16))
    exp_ok = None
    if exp:
        outside = [(o, n) for (o, n) in elf_hits
                   if not any(s <= o and o + n <= s + l for (s, l) in exp)]
        covered = [any(s <= o < s + l for (o, _n) in elf_hits) for (s, l) in exp]
        exp_ok = (not outside) and all(covered)
        print('\n  ELF 内差异段: %s' % ', '.join('0x%X(%dB)' % (o, n) for (o, n) in elf_hits))
        print('  期望落在这些串里: %s' % ', '.join('0x%X+%d' % e for e in exp))
        print('  串外差异 %d 个; 每条串都有差异: %s ⇒ %s'
              % (len(outside), covered, '✓' if exp_ok else '✗'))
    print('')
    print('  字库像素容器内      : %d B' % pix_bytes)
    print('  FONT.RES 槽内       : %d B' % ft_bytes)
    print('  登记容器内 (允许)   : %d B  %s'
          % (sum(allowed_containers.values()),
             ', '.join('%s=%dB' % kv for kv in sorted(allowed_containers.items())) or '无'))
    print('  允许区间合计        : %d B' % allowed)
    print('  总差异              : %d B' % tot)
    print('  允许区间之外        : %d B  %s' % (others, '✓' if others == 0 else '✗'))
    print('  ELF (真实 37.5MB)   : %d B / %d 段  %s'
          % (elf_bytes, len(elf_hits), '✓ (全部是短串)' if exp_ok in (True, None) else '✗'))
    print('  PVD (LBA16..17)     : %d B  %s' % (pvd_bytes, '✓' if pvd_bytes == 0 else '✗'))
    print('  两个 IMG 条目表      : %d B  %s' % (tab_bytes, '✓' if tab_bytes == 0 else '✗'))
    print('  GR.IMG#551..#565    : %d B  %s' % (n551_bytes, '✓' if n551_bytes == 0 else '✗'))
    doc = dict(a=a.a, b=a.b, sha_a=tcslib.sha256_file(a.a), sha_b=tcslib.sha256_file(a.b),
               diff_bytes=tot, diff_spans=len(merged), elf=(elf0, elf1),
               elf_diff_bytes=elf_bytes, elf_diff_spans=len(elf_hits),
               elf_diff_list=elf_hits, expect_elf_short=exp, expect_elf_short_ok=exp_ok,
               elf_window_round56=[295 * SEC, 295 * SEC + 0x180000],
               pvd_bytes=pvd_bytes, img_table_bytes=tab_bytes, gr_551_565_bytes=n551_bytes,
               pixel_container_bytes=pix_bytes, font_res_bytes=ft_bytes,
               allowed_bytes=allowed, other_bytes=others,
               by_container=dict((k, dict(bytes=v['bytes'], spans=v['spans']))
                                 for k, v in by.items()))
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
