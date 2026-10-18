# -*- coding: utf-8 -*-
r"""nh_iso_diff.py — 全盘逐字节差异图 (只读)

对两份 ISO 做分层差异定位:
  1 MB 块 → 若不同再下钻 64 KB → 4 KB → 逐字节 run
输出差异 run 列表 [(start, end)] 以及按"落在哪个 ISO9660 文件/区域"的分类汇总。

用法: python nh_iso_diff.py <tagA> <tagB>
"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(N.EVID, exist_ok=True)

MB = 1 << 20
K64 = 1 << 16
K4 = 1 << 12


def hexdump(b, base=0, n=64):
    out = []
    for i in range(0, min(len(b), n), 16):
        chunk = b[i:i + 16]
        out.append('    %08X  %-47s  %s'
                   % (base + i, ' '.join('%02X' % c for c in chunk),
                      ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)))
    return '\n'.join(out)


def diff_runs(a, b, size):
    """→ (runs, nbytes). runs = [(start, end_exclusive)]"""
    runs = []
    cur = None
    for off in range(0, size, MB):
        n = min(MB, size - off)
        ba = a.mm[off:off + n]
        bb = b.mm[off:off + n]
        if ba == bb:
            if cur is not None:
                runs.append((cur, off))
                cur = None
            continue
        # 下钻
        for o2 in range(0, n, K4):
            n2 = min(K4, n - o2)
            o = off + o2
            if a.mm[o:o + n2] == b.mm[o:o + n2]:
                if cur is not None:
                    runs.append((cur, o))
                    cur = None
                continue
            # 逐字节
            x = a.mm[o:o + n2]
            y = b.mm[o:o + n2]
            i = 0
            while i < n2:
                if x[i] != y[i]:
                    j = i
                    while j < n2 and x[j] != y[j]:
                        j += 1
                    if cur is None:
                        cur = o + i
                    # 相邻 run 合并留给外层
                    if runs and runs[-1][1] >= o + i:
                        pass
                    i = j
                else:
                    i += 1
            # run 边界在 4K 块内: 用 cur 连续拼接
            if cur is not None:
                runs.append((cur, o + n2))
                cur = None
    if cur is not None:
        runs.append((cur, size))
    # 合并相邻/重叠
    merged = []
    for s, e in runs:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def classify(iso, runs):
    """把 run 归到 ISO9660 文件 / 区域"""
    files = iso.files()
    pv = iso.pvd()
    regions = []
    for p, f in files.items():
        if f['flags'] & 2:
            continue
        regions.append((f['lba'] * N.SEC, f['lba'] * N.SEC + f['size'], p))
    regions.append((16 * N.SEC, 17 * N.SEC, '<PVD>'))
    regions.append((pv['root_lba'] * N.SEC, pv['root_lba'] * N.SEC + pv['root_size'], '<ROOTDIR>'))
    regions.append((pv['path_lba'] * N.SEC, pv['path_lba'] * N.SEC + pv['path_size'], '<PATHTABLE>'))
    regions.append((0, 16 * N.SEC, '<SYSTEM_AREA LBA0-15>'))
    regions.append((pv['vol_size'] * N.SEC, iso.size, '<BEYOND PVD vol_size>'))
    regions.sort()

    buckets = {}
    outdetail = []
    for (s, e) in runs:
        hit = []
        for (rs, re_, rp) in regions:
            if s < re_ and e > rs:
                hit.append(rp)
        # 归到最大的那个 (菜单/GR.IMG 会覆盖其它)
        key = hit[-1] if hit else '<UNMAPPED>'
        for rp in hit:
            if rp.endswith('.IMG;1'):
                key = rp
        buckets.setdefault(key, [0, 0, []])
        buckets[key][0] += 1
        buckets[key][1] += (e - s)
        if len(buckets[key][2]) < 400:
            buckets[key][2].append((s, e))
        outdetail.append((s, e, key))
    return buckets, outdetail


def main():
    tagA, tagB = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('EN_ORIG', 'ZH113b_fix')
    a = N.Iso(N.ISO[tagA])
    b = N.Iso(N.ISO[tagB])
    assert a.size == b.size, '尺寸不同 %d vs %d' % (a.size, b.size)
    runs = diff_runs(a, b, a.size)
    tot = sum(e - s for s, e in runs)
    buf = io.StringIO()
    buf.write('全盘逐字节差异: %s  vs  %s\n' % (tagA, tagB))
    buf.write('  A=%s\n  B=%s\n' % (a.path, b.path))
    buf.write('  文件尺寸 %s B (%d 扇区), 相同\n' % (N.fmt(a.size), a.sectors))
    buf.write('  差异 run 数 = %d, 差异总字节 = %s (占全盘 %.6f%%)\n'
              % (len(runs), N.fmt(tot), 100.0 * tot / a.size))
    buckets, detail = classify(b, runs)
    buf.write('\n按区域汇总 (用 B 盘的文件树映射):\n')
    for k in sorted(buckets, key=lambda k: -buckets[k][1]):
        n, nb, lst = buckets[k]
        buf.write('  %-34s runs=%-6d bytes=%-12s\n' % (k, n, N.fmt(nb)))
    buf.write('\n全部差异 run (start, end, len, 区域):\n')
    for (s, e, k) in detail:
        buf.write('  0x%09X-0x%09X  len=%-10s LBA %d..%d  %s\n'
                  % (s, e, N.fmt(e - s), s // N.SEC, (e - 1) // N.SEC, k))
    # 每个 run 的首尾 64B 对照
    buf.write('\n差异内容样本 (每 run 前 64 B):\n')
    for (s, e, k) in detail:
        buf.write('--- [0x%X-0x%X) len=%d  %s\n' % (s, e, e - s, k))
        buf.write('  A(%s):\n%s\n' % (tagA, hexdump(a.mm[s:s + 64], s)))
        buf.write('  B(%s):\n%s\n' % (tagB, hexdump(b.mm[s:s + 64], s)))
    fn = os.path.join(N.EVID, 'stage2_isodiff_%s_vs_%s.txt' % (tagA, tagB))
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())
    print(buf.getvalue()[:20000])
    print('... full → %s' % fn)
    a.close()
    b.close()


if __name__ == '__main__':
    main()
