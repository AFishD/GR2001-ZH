# -*- coding: utf-8 -*-
r"""iso_bytes_diff.py — 两张 ISO 的**全盘逐字节**对比, 并把差异归类到"盘上结构"。

用法:
  python iso_bytes_diff.py <A.iso> <B.iso> [--json <out.json>]

输出:
  · 差异字节总数 / 差异区间 (合并相邻) / 每个区间的 offset(绝对与 ISO 内 LBA+偏移);
  · 归类: 落在 COMMON.PAK 的 new_font_revised 像素容器内 (含在哪个 4bit 字节、哪一行) /
    落在别处 (ELF / IMG 条目表 / PAK 包头 / 文本区 / 制作组名单 …) ⇒ 后者必须为 0。
  · 逐区间的"期望行": 像素容器里 y = off_in_container*2 // 1024。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                       # noqa: E402


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
    offs = []
    nbytes = 0
    same = 0
    while True:
        ba = fa.read(CH)
        bb = fb.read(CH)
        if not ba:
            break
        if ba == bb:
            same += len(ba)
            continue
        base = fa.tell() - len(ba)
        for i in range(len(ba)):
            if ba[i] != bb[i]:
                offs.append(base + i)
        nbytes = len(offs)
    fa.close()
    fb.close()
    print('相同字节 %d (%.2f%%); **差异字节 %d**' % (same, same * 100.0 / szA, nbytes))

    # ---------- 定位 COMMON.PAK 的像素容器 ----------
    iso = tcslib.Iso(A)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
        elif e['name'] == 'FONT.RES':
            ft_e = e
        if pak_e and ft_e:
            break
    iso.close()
    assert pak_e, 'A 盘里找不到 COMMON.PAK'
    pak = tcslib.Iso(A).read(pak_e['iso_off'], pak_e['stored'])
    rec = [r for r in tcslib.parse_pak_records(pak) if r[0] == 'new_font_revised']
    assert len(rec) == 1
    _nm, psm, w, h, clut, px_size, PX = rec[0]
    print('COMMON.PAK: iso_off=0x%X stored=%d | 像素容器 px_off=0x%X %dx%d psm=0x%02X'
          % (pak_e['iso_off'], pak_e['stored'], PX, w, h, psm))
    c0 = pak_e['iso_off'] + PX
    c1 = c0 + w * h // 2
    assert c1 <= pak_e['iso_off'] + pak_e['stored'], '像素容器越界?'

    inside = [o for o in offs if c0 <= o < c1]
    outside = [o for o in offs if not (c0 <= o < c1)]
    print('')
    print('像素容器范围: 0x%X .. 0x%X (长度 %d B)' % (c0, c1 - 1, c1 - c0))
    print('  ├ 容器内差异 %d 字节' % len(inside))
    print('  └ **容器外差异 %d 字节** (期望 0)' % len(outside))

    # ---------- 用盘上真实分段表把"容器字节"反解成 (y 行, x 列) ----------
    blob = pak[PX:PX + w * h // 2]
    segs = tcslib.atlas_container_segments(blob, w // 2)
    print('容器分段 %d 个: %s' % (len(segs), [(a, b, c) for a, b, c in segs]))

    def rev(bo):
        """容器内字节偏移 → (行, x0, x1); 不在任何段数据区则 None。"""
        for first_row, doff, nbytes in segs:
            if doff <= bo < doff + nbytes:
                rel = bo - doff
                return (first_row + rel // (w // 2), (rel % (w // 2)) * 2)
        return None

    fo = open(A, 'rb'); fb2 = open(B, 'rb')
    nib = 0
    texels = []
    for o in inside:
        fo.seek(o); fb2.seek(o)
        va = fo.read(1)[0]; vb = fb2.read(1)[0]
        for half in (0, 1):
            if (va >> (4 * half)) & 0xF != (vb >> (4 * half)) & 0xF:
                nib += 1
                rv = rev(o - c0)
                if rv:
                    texels.append((rv[0], rv[1] + half))
    fo.close(); fb2.close()

    recs = []
    for (s, e) in ranges(offs):
        rs = [o for o in offs if s <= o <= e]
        rr = [rev(o - c0) for o in rs]
        rows = sorted(set(r[0] for r in rr if r))
        recs.append(dict(off0=s, off1=e, n=e - s + 1,
                         in_container=bool(c0 <= s and e < c1),
                         c_off0=(s - c0) if c0 <= s < c1 else None,
                         rows=rows))
    print('')
    print('差异区间 %d 段:' % len(recs))
    for r in recs:
        print('  0x%08X..0x%08X (%2d B, iso_off)  容器内 off=%s  行=%s'
              % (r['off0'], r['off1'], r['n'],
                 ('%d..%d' % (r['c_off0'], r['c_off0'] + r['n'] - 1))
                 if r['c_off0'] is not None else '—', r['rows']))
    print('')
    print('**真正变化的 4bit texel 数 = %d** (在 %d 个容器字节里)' % (nib, len(inside)))
    print('全部差异落在容器 y 行: %s' % sorted(set(t[0] for t in texels)))
    print('这些 texel 的 x 范围: %d..%d' % (min(t[1] for t in texels), max(t[1] for t in texels)))
    doc = dict(A=os.path.abspath(A), B=os.path.abspath(B),
               size=szA, same_bytes=same, diff_bytes=nbytes,
               container=dict(iso_off=pak_e['iso_off'], px_off=PX, w=w, h=h,
                              c0=c0, c1=c1, segs=[[int(a), int(b), int(c)] for a, b, c in segs]),
               inside=len(inside), outside=len(outside),
               ranges=recs,
               outside_offsets=outside[:200],
               rows=sorted(set(t[0] for t in texels)),
               texels=nib,
               texel_xy=[[int(y), int(x)] for y, x in sorted(texels)])
    if outp:
        io.open(outp, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('→ %s' % outp)
    return 0 if not outside else 1


if __name__ == '__main__':
    sys.exit(main())
