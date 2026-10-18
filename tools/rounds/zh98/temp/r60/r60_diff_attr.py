# -*- coding: utf-8 -*-
r"""r60_diff_attr.py — GR_TEST_FONT1 vs GR_ZH109 的**差异归属** (按真实容器边界)。

判据 (round60 验收):
  · 全盘差异 > 0 (补丁确实动了东西);
  · **每一个**差异字节都完整落在 `MENU.IMG#283 EN_SPECIAL_FEATURE.XML` 的
    `[iso_off, iso_off+stored)` 内 (真实容器边界, 不是拍脑袋的窗口);
  · ELF (按 ELF 头的真实长度) / PVD / 两个 IMG 条目表 / FONT.RES 槽 /
    字库像素容器 / EN_STRINGS.RES 两份副本 / 制作组相关条目 = **差异 0 B**。

用法: python r60_diff_attr.py <A.iso> <B.iso> [--json out.json]
"""
import argparse
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import dump_font as DF                                                 # noqa: E402
import font_compact as FC                                              # noqa: E402
from iso_tools import TAB_OFF, TAB_STEP                               # noqa: E402

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
    ap.add_argument('--expect', default='MENU.IMG#283',
                    help='期望容纳全部差异的容器 (label 前缀)')
    a = ap.parse_args()

    iso_a, iso_b = tcslib.Iso(a.a), tcslib.Iso(a.b)
    sha_a, sha_b = tcslib.sha256_file(a.a), tcslib.sha256_file(a.b)
    print('A = %s  sha %s' % (os.path.basename(a.a), sha_a))
    print('B = %s  sha %s' % (os.path.basename(a.b), sha_b))

    regions = []
    names_all = {}
    for tag, lba in (('MENU.IMG', MENU_LBA), ('GR.IMG', GR_LBA)):
        n = FC.img_entry_count(iso_a, lba)
        names_all[tag] = []
        for idx in range(n):
            e = iso_a.img_entry(lba, idx)
            names_all[tag].append(e['name'])
            if e['stored'] <= 0 or e['stored'] > 0x7FFFFFFF:
                continue
            regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                            '%s#%d %s' % (tag, idx, e['name'])))
    regions.sort()
    tabs = [(MENU_LBA * SEC + TAB_OFF,
             MENU_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, MENU_LBA)),
            (GR_LBA * SEC + TAB_OFF,
             GR_LBA * SEC + TAB_OFF + TAB_STEP * FC.img_entry_count(iso_a, GR_LBA))]
    elf0, elf1 = elf_range(iso_a)
    PVD = (16 * SEC, 18 * SEC)
    f = DF.load_font(a.a)
    px = (f['pak_e']['iso_off'] + f['atlas']['px_off'],
          f['pak_e']['iso_off'] + f['atlas']['px_off'] + f['atlas']['px_size'])
    ft = (f['ft_e']['iso_off'], f['ft_e']['iso_off'] + f['ft_e']['stored'])
    # 制作组名单 / 文案表 (RES 两份副本) + 任何名字里带 CRED 的条目
    roi = {}
    for tag, lba, idx in (('MENU.IMG', MENU_LBA, 283), ('MENU.IMG', MENU_LBA, 25),
                          ('GR.IMG', GR_LBA, 902)):
        e = iso_a.img_entry(lba, idx)
        roi['%s#%d %s' % (tag, idx, e['name'])] = (e['iso_off'], e['iso_off'] + e['stored'])
    creds = [(o, t, nm) for (o, t, nm) in regions if 'CRED' in nm.upper()]
    for (o, t, nm) in creds:
        roi[nm] = (o, t)
    print('ELF 区间 (按 ELF 头) 0x%X..0x%X (%.1f MB); PVD 0x%X..0x%X'
          % (elf0, elf1, (elf1 - elf0) / 1e6, PVD[0], PVD[1]))
    print('字库像素容器 0x%X..0x%X (%d B); FONT.RES 槽 0x%X..0x%X (%d B)'
          % (px[0], px[1], px[1] - px[0], ft[0], ft[1], ft[1] - ft[0]))
    print('名字含 CRED 的条目: %s' % (', '.join(nm for _o, _t, nm in creds) or '(无)'))
    iso_a.close()
    iso_b.close()

    raw = diff_ranges(a.a, a.b)
    tot = sum(n for _o, n in raw)

    def owner(o, n):
        e = o + n
        if o >= px[0] and e <= px[1]:
            return '★字库像素容器'
        if o >= ft[0] and e <= ft[1]:
            return 'FONT.RES 槽'
        if o >= elf0 and e <= elf1:
            return 'ELF (真实长度)'
        if o >= PVD[0] and e <= PVD[1]:
            return 'PVD (LBA16..17)'
        for (s, t) in tabs:
            if o >= s and e <= t:
                return 'IMG 条目表'
        for (s, t, nm) in regions:
            if o >= s and e <= t:
                return nm
        return '(未归属)'

    by = {}
    for (o, n) in raw:
        by[owner(o, n)] = by.get(owner(o, n), 0) + n
    print('\n全盘差异: %d B / %d 段' % (tot, len(raw)))
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        print('   %-46s %9d B' % (k, v))

    expect = [x for x in a.expect.split(',') if x.strip()]
    ok_owner = all(any(k.startswith(x) for x in expect) for k in by)
    checks = [
        ('差异只落在 %s' % '/'.join(expect), ok_owner, '所有者集合 = %s' % sorted(by)),
        ('ELF 差异 0', by.get('ELF (真实长度)', 0) == 0, '%d B' % by.get('ELF (真实长度)', 0)),
        ('PVD 差异 0', by.get('PVD (LBA16..17)', 0) == 0, '%d B' % by.get('PVD (LBA16..17)', 0)),
        ('IMG 条目表差异 0', by.get('IMG 条目表', 0) == 0, '%d B' % by.get('IMG 条目表', 0)),
        ('FONT.RES 槽差异 0', by.get('FONT.RES 槽', 0) == 0, '%d B' % by.get('FONT.RES 槽', 0)),
        ('字库像素容器差异 0', by.get('★字库像素容器', 0) == 0,
         '%d B' % by.get('★字库像素容器', 0)),
        ('(未归属) 差异 0', by.get('(未归属)', 0) == 0, '%d B' % by.get('(未归属)', 0)),
    ]
    for nm, (s, t) in roi.items():
        if nm.startswith('MENU.IMG#283'):
            continue
        n = sum(k for k in raw if k[0] >= s and k[0] + k[1] <= t)
        checks.append(('「%s」差异 0' % nm, n == 0, '%d B' % n))
    print('')
    allok = True
    for nm, ok, det in checks:
        allok = allok and ok
        print('  [%s] %-34s %s' % ('✓' if ok else '✗', nm, det))
    doc = dict(a=a.a, b=a.b, sha_a=sha_a, sha_b=sha_b, diff_bytes=tot, diff_spans=len(raw),
               by_owner=by, checks=[dict(name=nm, ok=ok, detail=det) for nm, ok, det in checks],
               all_ok=allok, ranges=raw[:200],
               regions=dict(elf=[elf0, elf1], pvd=list(PVD), pixel=list(px), font_res=list(ft),
                            roi={k: list(v) for k, v in roi.items()}))
    if a.json:
        io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % a.json)
    print('\n[结论] %s' % ('差异归属 ✓ 全部落在 %s 内' % '/'.join(expect) if allok else '★ 有差异越界'))
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
