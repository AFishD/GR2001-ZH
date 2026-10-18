# -*- coding: utf-8 -*-
r"""cvar_owner.py — 把差异区间精确归属到结构 (最小包含区间优先)

用法: python cvar_owner.py --a <EN.iso> --b <ZH.iso> --diff <runs.json> [--out <txt>]

归属层级 (从具体到宽泛):
  IMG 条目 (off .. off+max(stored,real))  ← 最小包含区间优先
  IMG 名字表 / 条目表 / 头 / 条目表前方空白
  ISO9660 目录记录 / PVD / 系统区
  <IMG 空隙> (落在 IMG 内但不在任何条目范围)
  <ISO 空隙>
"""
import argparse
import json
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}


def ents(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    return [(nm, list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i)))
            for i, nm in enumerate(names)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--diff', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--list-for', default=None, help='列出包含此 ISO 偏移的所有条目')
    x = ap.parse_args()
    A = open(x.a, 'rb').read()
    D = json.load(open(x.diff, encoding='utf-8'))
    runs = [(a, b) for a, b in D['runs']]
    L = []
    P = lambda s: (print(s), L.append(s))

    # ---- ISO 文件区间
    pvd = 16 * SEC
    root_lba = struct.unpack_from('<I', A, pvd + 158)[0]
    root_size = struct.unpack_from('<I', A, pvd + 166)[0]

    def readdir(lba, size):
        out = []
        data = A[lba * SEC:lba * SEC + size]
        i = 0
        while i < len(data):
            Ln = data[i]
            if Ln == 0:
                i = (i // SEC + 1) * SEC
                if i >= len(data):
                    break
                continue
            if i + Ln > len(data) or Ln < 34:
                break
            rec = data[i:i + Ln]
            out.append((rec[33:33 + rec[32]],
                        struct.unpack_from('<I', rec, 2)[0],
                        struct.unpack_from('<I', rec, 10)[0], rec[25],
                        lba * SEC + i, Ln))
            i += Ln
        return out

    iso_files = []
    dirrecs = []

    def walk(lba, size, prefix):
        for nm, ext, sz, fl, ao, Ln in readdir(lba, size):
            if nm in (b'\x00', b'\x01'):
                continue
            name = nm.decode('latin-1')
            p = (prefix + '/' + name) if prefix else name
            dirrecs.append((p, ao, Ln))
            if fl & 2:
                walk(ext, sz, p)
            else:
                iso_files.append((p, ext * SEC, ext * SEC + sz, ext, sz))
    walk(root_lba, root_size, '')
    iso_files.sort(key=lambda z: z[1])

    # ---- IMG 区间
    intervals = []          # (start, end, label, kind)
    for nm, lba in IMG_LBA.items():
        b = lba * SEC
        h = struct.unpack_from('<8I', A, b)
        E = ents(A, lba)
        intervals.append((b, b + TAB_OFF, '%s 头 [0,0x830)' % nm, 'P5-img-header'))
        noff = struct.unpack_from('<I', A, b + 0x10)[0]
        nend = struct.unpack_from('<I', A, b + 0x04)[0]
        intervals.append((b + noff, b + nend, '%s 名字表' % nm, 'P5-img-names'))
        intervals.append((b + TAB_OFF, b + TAB_OFF + TAB_STEP * len(E),
                          '%s 条目表 (%d 条)' % (nm, len(E)), 'P5-img-table'))
        for i, (n2, f) in enumerate(E):
            if f[8] and max(f[6], f[7]):
                intervals.append((b + f[8], b + f[8] + max(f[6], f[7]),
                                  '%s::%s [#%d]' % (nm, n2, i), 'img-entry'))
        isz = [t for t in iso_files if t[0] == nm]
        if isz:
            intervals.append((isz[0][1], isz[0][2], '%s 内部(未归属)' % nm, 'img-gap'))
    intervals.sort(key=lambda z: (z[1] - z[0]))   # 最小优先

    def find_all(off, maxn=12):
        return [t for t in intervals if t[0] <= off < t[1]]

    if x.list_for:
        o = int(x.list_for, 16)
        print('ISO 0x%X 处被以下区间包含:' % o)
        for s, e, lb, kd in find_all(o):
            print('   [%s] %-40s 0x%X..0x%X (len %d)  rel=+0x%X' % (kd, lb, s, e, e - s, o - s))

    def classify(s, e):
        mid = (s + e) // 2
        cand = find_all(mid)
        # 优先 IMG 条目 (最小者), 其次 IMG 表/头, 再 ISO 文件, 最后空隙
        for pref in ('img-entry', 'P5-img-table', 'P5-img-names', 'P5-img-header'):
            for t in cand:
                if t[3] == pref:
                    return t[2], t[3]
        for t in cand:
            if t[3] == 'img-gap':
                return t[2], 'IMG空隙'
        for f in iso_files:
            if f[1] <= mid < f[2]:
                return f[0], 'iso-file'
        for p, ao, Ln in dirrecs:
            if ao <= mid < ao + Ln:
                return 'ISO9660 目录记录 %s' % p, 'P5-iso-dirrec'
        return '<其它/结构外侧>', 'other'

    agg = {}
    for s, e in runs:
        lb, kd = classify(s, e)
        a = agg.setdefault(lb, [0, 0, s, e, kd])
        a[0] += 1
        a[1] += e - s
        a[2] = min(a[2], s)
        a[3] = max(a[3], e)
    P('== 差异归属 (最小包含区间优先) ==')
    for k in sorted(agg, key=lambda z: -agg[z][1]):
        c, b, lo, hi, kd = agg[k]
        P('  %-38s [%-14s] runs=%-6d bytes=%-9d ISO 0x%09X..0x%09X'
          % (k, kd, c, b, lo, hi))

    # 每个 ISO9660 文件内的差异字节数
    P('\n== 每个 ISO9660 文件内的差异 ==')
    for name, s0, e0, lba, sz in iso_files:
        c = b = 0
        lo = hi = None
        for s, e in runs:
            m = (s + e) // 2
            if s0 <= m < e0:
                c += 1
                b += e - s
                lo = s if lo is None else min(lo, s)
                hi = e if hi is None else max(hi, e)
        if c:
            P('  %-24s LBA=%-8d size=%-10d runs=%-6d bytes=%-9d 0x%09X..0x%09X'
              % (name, lba, sz, c, b, lo, hi))
    P('\n== 无差异的文件 ==')
    P('  ' + ', '.join(n for n, s0, e0, lba, sz in iso_files
                       if not any(s0 <= (s + e) // 2 < e0 for s, e in runs)))
    if x.out:
        with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(L) + '\n')
        print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
