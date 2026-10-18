# -*- coding: utf-8 -*-
r"""diff_r54.py — 两张 ISO 全盘逐字节对比 + 差异归属 (round54 验收用)。

= `work/builds/GR_ZH98/temp/verify/iso_bytes_diff.py` 的 round54 版 (`check_protected_ranges.py` 的
  口径合并进来), 因为本轮的改动**允许**落在两处:
    · COMMON.PAK → new_font_revised 的**像素容器**;
    · MENU.IMG → **FONT.RES** 槽 (FT 记录表重压后的帧字节)。
  其它任何地方 (ELF / PVD / 两个 IMG 条目表 / GR.IMG #551..#565 制作组名单 / PAK 头 / 文本区 …)
  必须 **0 字节差异**。

用法: python diff_r54.py <A.iso> <B.iso> [--json <out.json>]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                 # noqa: E402
import tcslib                                                        # noqa: E402


def ranges(off):
    out = []
    if not off:
        return out
    s = p = off[0]
    for o in off[1:]:
        if o == p + 1:
            p = o
            continue
        out.append((s, p))
        s = p = o
    out.append((s, p))
    return out


def main():
    argv = sys.argv[1:]
    a = [x for x in argv if not x.startswith('--')]
    A, B = a[0], a[1]
    outp = argv[argv.index('--json') + 1] if '--json' in argv else None
    szA, szB = os.path.getsize(A), os.path.getsize(B)
    print('A = %s (%d B)' % (A, szA))
    print('B = %s (%d B)' % (B, szB))
    assert szA == szB, '尺寸不同!'
    fa, fb = open(A, 'rb'), open(B, 'rb')
    CH = 1 << 22
    offs, same = [], 0
    while True:
        ba, bb = fa.read(CH), fb.read(CH)
        if not ba:
            break
        if ba == bb:
            same += len(ba)
            continue
        base = fa.tell() - len(ba)
        offs.extend(base + i for i in range(len(ba)) if ba[i] != bb[i])
    fa.close()
    fb.close()
    print('相同字节 %d (%.4f%%); **差异字节 %d**' % (same, same * 100.0 / szA, len(offs)))

    w = D.load_font(A)
    pak_e, ft_e, ad = w['pak_e'], w['ft_e'], w['atlas']
    c0, c1 = pak_e['iso_off'] + ad['px_off'], pak_e['iso_off'] + ad['px_off'] + ad['px_size']
    f0, f1 = ft_e['iso_off'], ft_e['iso_off'] + ft_e['stored']
    print('COMMON.PAK 像素容器 0x%X..0x%X (px_size %d); FONT.RES 槽 0x%X..0x%X (stored %d)'
          % (c0, c1 - 1, ad['px_size'], f0, f1 - 1, ft_e['stored']))

    def n_in(lo, hi):
        return sum(1 for o in offs if lo <= o < hi)

    inside = n_in(c0, c1)
    in_ft = n_in(f0, f1)
    outside = [o for o in offs if not (c0 <= o < c1) and not (f0 <= o < f1)]
    print('')
    print('  ├ 像素容器内差异 %d 字节 (改 %d 个 4bit texel 的容器字节)'
          % (inside, inside))
    print('  ├ FONT.RES 槽内差异 %d 字节' % in_ft)
    print('  └ **两处之外差异 %d 字节** (期望 0)' % len(outside))
    for o in outside[:40]:
        print('       !! 0x%08X' % o)

    # ---- 敏感区域逐条核对 ----
    iso = tcslib.Iso(A)
    regions = [
        ('ELF (程序, LBA 295 起 1 MB)', 295 * 2048, 295 * 2048 + (1 << 20)),
        ('ISO PVD + 卷描述符 (LBA 16..19)', 16 * 2048, 20 * 2048),
        ('MENU.IMG 条目表本体 (IMG 起始 0x4000 B)', tcslib.MENU_LBA * 2048,
         tcslib.MENU_LBA * 2048 + 0x4000),
        ('GR.IMG 条目表本体 (IMG 起始 0x4000 B)', tcslib.GR_LBA * 2048,
         tcslib.GR_LBA * 2048 + 0x4000),
        ('COMMON.PAK 头部 (像素容器之前)', pak_e['iso_off'], c0),
        ('COMMON.PAK 像素容器之后 (含 16B 容器尾 + PAK 其余)',
         c1, pak_e['iso_off'] + pak_e['stored']),
    ]
    for i in range(551, 566):
        e = iso.img_entry(tcslib.GR_LBA, i)
        if e:
            regions.append(('GR.IMG #%d %s (制作组名单段)' % (i, e['name']),
                            e['iso_off'], e['iso_off'] + e['stored']))
    iso.close()
    print('')
    bad = 0
    reg_rows = []
    for name, lo, hi in regions:
        n = n_in(lo, hi)
        bad += 1 if n else 0
        print('  %s%-56s [0x%09X,0x%09X) 差异 %d' % ('OK ' if not n else '!! ', name, lo, hi, n))
        reg_rows.append(dict(name=name, lo=lo, hi=hi, diff=n))
    print('')
    print('**敏感区域 %d 个; 含差异的 %d 个**' % (len(regions), bad))

    recs = [dict(off0=s, off1=e, n=e - s + 1,
                 in_container=bool(c0 <= s and e < c1),
                 in_ft=bool(f0 <= s and e < f1))
            for (s, e) in ranges(offs)]
    print('差异区间 %d 段' % len(recs))
    for r in recs[:12]:
        print('   0x%08X..0x%08X (%d B) 容器内=%s FONT.RES内=%s'
              % (r['off0'], r['off1'], r['n'], r['in_container'], r['in_ft']))
    doc = dict(A=os.path.abspath(A), B=os.path.abspath(B), size=szA, same=same,
               diff_bytes=len(offs), container=dict(c0=c0, c1=c1, px_off=ad['px_off'],
                                                    px_size=ad['px_size'], diff=inside),
               font_res=dict(iso_off=f0, stored=ft_e['stored'], diff=in_ft),
               outside=len(outside), regions=reg_rows, ranges=recs,
               outside_offsets=outside[:200])
    if outp:
        io.open(outp, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % outp)
    return 0 if (not outside and bad == 0) else 1


if __name__ == '__main__':
    sys.exit(main())
