# -*- coding: utf-8 -*-
r"""cvar_semdiff.py — 紧凑结构化对比 EN_ORIG vs ZH113b 并把差异区间归属到部件

用法: python cvar_semdiff.py --a <EN.iso> --b <ZH.iso> --diff <runs.json> [--out <md>]

输出 (紧凑):
  [0] ISO9660 层面: PVD / 目录记录字节比对 / 文件表 (path,lba,size) 差异
  [1] MENU.IMG / GR.IMG: 头字段差异, 名字表差异, 条目表字段差异 (只列变化的)
  [2] 把 diff runs 归属到部件
"""
import argparse
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}
EN = {'MENU.IMG': 776286, 'GR.IMG': 19175}
FLD = ['f0', 'f1', 'f2', 'f3', 'f4', 'f5(STORED)', 'f6(REAL)', 'f7', 'f8(OFF)',
       'f9', 'f10', 'f11']


def pvd(d):
    p = 16 * SEC
    return {'vol_space': struct.unpack_from('<I', d, p + 80)[0],
            'root_lba': struct.unpack_from('<I', d, p + 158)[0],
            'root_size': struct.unpack_from('<I', d, p + 166)[0],
            'path_lba': struct.unpack_from('<I', d, p + 140)[0],
            'path_size': struct.unpack_from('<I', d, p + 132)[0]}


def read_dir(d, lba, size):
    out = []
    data = d[lba * SEC:lba * SEC + size]
    i = 0
    while i < len(data):
        L = data[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(data):
                break
            continue
        if i + L > len(data) or L < 34:
            break
        rec = data[i:i + L]
        out.append((rec[33:33 + rec[32]], struct.unpack_from('<I', rec, 2)[0],
                    struct.unpack_from('<I', rec, 10)[0], rec[25], lba * SEC + i, L))
        i += L
    return out


def walk(d, lba, size, prefix, acc):
    for nm, ext, sz, fl, ao, L in read_dir(d, lba, size):
        if nm in (b'\x00', b'\x01'):
            continue
        name = nm.decode('latin-1')
        p = (prefix + '/' + name) if prefix else name
        acc.append({'path': p, 'lba': ext, 'size': sz, 'is_dir': bool(fl & 2),
                    'dirrec_off': ao, 'dirrec_len': L, 'name_len': len(nm)})
        if fl & 2:
            walk(d, ext, sz, p, acc)
    return acc


def entries(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        out.append((nm, list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i))))
    return out, noff, nend


def hdr(d, lba):
    b = lba * SEC
    return dict(zip(['h00', 'h04', 'h08', 'h0c', 'h10', 'h14', 'h18', 'h1c'],
                    struct.unpack_from('<8I', d, b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--diff', required=True)
    ap.add_argument('--out', default=None)
    x = ap.parse_args()
    A = open(x.a, 'rb').read()
    B = open(x.b, 'rb').read()
    L = []
    P = lambda s: (print(s), L.append(s))
    D = json.load(open(x.diff, encoding='utf-8'))
    runs = [(a, b) for a, b in D['runs']]

    # ---- [0] ISO9660
    pa, pb = pvd(A), pvd(B)
    P('[0] ISO9660')
    P('  PVD EN  = %s' % pa)
    P('  PVD ZH  = %s  identical=%s' % (pb, pa == pb))
    # 目录记录字节区间
    fa = walk(A, pa['root_lba'], pa['root_size'], '', [])
    fb = walk(B, pb['root_lba'], pb['root_size'], '', [])
    m = {f['path']: f for f in fa}
    n = {f['path']: f for f in fb}
    P('  文件数 EN=%d ZH=%d 路径集合相同=%s' % (len(fa), len(fb), set(m) == set(n)))
    ch = []
    for p in sorted(set(m) | set(n)):
        u, v = m.get(p), n.get(p)
        if u is None or v is None:
            ch.append((p, 'only in %s' % ('EN' if u is None else 'ZH'), u, v))
        elif (u['lba'], u['size']) != (v['lba'], v['size']):
            ch.append((p, 'lba/size', u, v))
    P('  文件表 (LBA/size) 变化条数 = %d' % len(ch))
    for p, why, u, v in ch:
        P('    %-24s %s  EN(lba=%s,size=%s) ZH(lba=%s,size=%s)'
          % (p, why, u and u['lba'], u and u['size'], v and v['lba'], v and v['size']))
    # 目录记录区域的逐字节比较
    dr_ch = 0
    dr_ranges = []
    for p in sorted(set(m) & set(n)):
        u, v = m[p], n[p]
        if u['dirrec_off'] != v['dirrec_off'] or u['dirrec_len'] != v['dirrec_len']:
            P('    !! 目录记录位置不同 %s' % p)
            continue
        o, ln = u['dirrec_off'], u['dirrec_len']
        if A[o:o + ln] != B[o:o + ln]:
            dr_ch += 1
            dr_ranges.append((p, o, ln))
    # 整个 root 目录区 + PVD 区的字节比较
    sysarea = [(0, 256 * SEC, 'LBA 0..255 系统/保护区'),
               (16 * SEC, 17 * SEC, 'PVD'),
               (pa['root_lba'] * SEC, pa['root_lba'] * SEC + pa['root_size'], '根目录区')]
    for s, e, nm in sysarea:
        same = A[s:e] == B[s:e]
        P('  %-22s 0x%09X..0x%09X 逐字节相同=%s' % (nm, s, e, same))
        if not same:
            d = [i for i in range(e - s) if A[s + i] != B[s + i]]
            P('      其中不同字节 %d 个, 范围 +0x%X..+0x%X' % (len(d), d[0], d[-1]))
    P('  目录记录 (name/lba/size/flags) 字节有变化的条目 = %d %s'
      % (dr_ch, [r[0] for r in dr_ranges]))

    # ---- [1] IMG
    P('\n[1] IMG 容器内部')
    for nm in ('MENU.IMG', 'GR.IMG'):
        lba = IMG_LBA[nm]
        ha, hb = hdr(A, lba), hdr(B, lba)
        P('  %s @LBA %d iso=0x%X' % (nm, lba, lba * SEC))
        for k in ha:
            if ha[k] != hb[k]:
                P('    头 %s: EN=0x%X(%d) → ZH=0x%X(%d)' % (k, ha[k], ha[k], hb[k], hb[k]))
        ea, na1, ne1 = entries(A, lba)
        eb, na2, ne2 = entries(B, lba)
        P('    名字表 [0x%X,0x%X) vs [0x%X,0x%X); 条目 EN=%d ZH=%d'
          % (na1, ne1, na2, ne2, len(ea), len(eb)))
        names_a = [e[0] for e in ea]
        names_b = [e[0] for e in eb]
        P('    名字序列相同=%s' % (names_a == names_b))
        if names_a != names_b:
            for i in range(max(len(names_a), len(names_b))):
                ga = names_a[i] if i < len(names_a) else None
                gb = names_b[i] if i < len(names_b) else None
                if ga != gb:
                    P('      [%d] %r → %r' % (i, ga, gb))
        # 名字表字节比较
        sa = A[lba * SEC + na1:lba * SEC + ne1]
        sb = B[lba * SEC + na2:lba * SEC + ne2]
        P('    名字表字节相同=%s (EN %d B / ZH %d B)' % (sa == sb, len(sa), len(sb)))
        # 条目表字段对比
        nch = 0
        for i in range(min(len(ea), len(eb))):
            if ea[i][1] != eb[i][1]:
                diffs = [(FLD[j], ea[i][1][j], eb[i][1][j])
                         for j in range(12) if ea[i][1][j] != eb[i][1][j]]
                nch += 1
                if nch <= 40:
                    P('      [%4d] %-20s %s' % (i, ea[i][0],
                                                ' '.join('%s:%X→%X' % d for d in diffs)))
        P('    ★ 条目字段变化条数 = %d / %d' % (nch, min(len(ea), len(eb))))
        # 名字表+条目表 覆盖的 ISO 区间
        t0 = lba * SEC
        P('    表区 ISO 0x%X..0x%X (名字) / 0x%X..0x%X (条目)'
          % (t0 + na1, t0 + ne1, t0 + TAB_OFF, t0 + TAB_OFF + TAB_STEP * max(len(ea), len(eb))))

    # ---- [2] 归属
    P('\n[2] 差异区间归属')
    # 构建 归属函数: 列出 EN 侧结构
    def structs(d):
        p = pvd(d)
        fs = walk(d, p['root_lba'], p['root_size'], '', [])
        out = [('ISO系统区 0..0x20000', 0, 0x20000, 'P5')]
        for f in fs:
            if f['is_dir']:
                continue
            out.append((f['path'], f['lba'] * SEC, f['lba'] * SEC + f['size'], '?'))
        for nm, lba in IMG_LBA.items():
            e, no, ne = entries(d, lba)
            t = lba * SEC
            out.append(('%s 头 [0,0x830)' % nm, t, t + TAB_OFF, 'P5'))
            out.append(('%s 名字表' % nm, t + no, t + ne, 'P5'))
            out.append(('%s 条目表' % nm, t + TAB_OFF, t + TAB_OFF + TAB_STEP * len(e), 'P5'))
            for i, (n2, f) in enumerate(e):
                if f[8] and max(f[6], f[7]):
                    out.append(('%s::%s [#%d]' % (nm, n2, i),
                                t + f[8], t + f[8] + max(f[6], f[7]), '?'))
        return out

    SA = structs(A)
    SA.sort(key=lambda z: z[1])

    def owner(off, tbl):
        lo, hi = 0, len(tbl)
        while lo < hi:
            mid = (lo + hi) // 2
            if tbl[mid][1] <= off:
                lo = mid + 1
            else:
                hi = mid
        for k in range(lo - 1, max(-1, lo - 6), -1):
            if tbl[k][1] <= off < tbl[k][2]:
                return tbl[k][0]
        return None

    agg = {}
    for s, e in runs:
        o = owner((s + e) // 2, SA) or '<未归属>'
        a = agg.setdefault(o, [0, 0, s, e])
        a[0] += 1
        a[1] += e - s
        a[2] = min(a[2], s)
        a[3] = max(a[3], e)
    for k in sorted(agg, key=lambda z: -agg[z][1]):
        c, b, lo, hi = agg[k]
        P('  %-34s runs=%-6d bytes=%-9d 0x%09X..0x%09X' % (k, c, b, lo, hi))
    if x.out:
        with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(L) + '\n')
        print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
