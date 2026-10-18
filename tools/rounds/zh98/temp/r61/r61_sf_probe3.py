# -*- coding: utf-8 -*-
r"""r61_sf_probe3.py — 把"行号"的三种编码一起试: u32 / float32 / u8(低字节)。

r61_diff_rows 只试了 u32 与 u8 的**整数**解释; 若引擎把当前下标存成 float
(1.0f/2.0f/…), 或存成别的宽度, 就会漏掉。本脚本对每个 4 字节对齐位置同时按
u32 与 float32 解释, 并对低字节按 u8 解释, 一起跟假设序列比。

用法: python work/builds/GR_ZH98/temp/r61/r61_sf_probe3.py <dumpdir> [prefix]
"""
import glob
import os
import sys

import numpy as np

HYPS = {
    'sf1': [1, 2, 3, 4, 5, 6, 8, 9, 10],
    'sf0': [0, 1, 2, 3, 4, 5, 7, 8, 9],
    'sford': [0, 1, 2, 3, 4, 5, 6, 7, 8],
    'sf1m1': [0, 1, 2, 3, 4, 5, 7, 8, 9],
    'sfrev': [10, 9, 8, 6, 5, 4, 3, 2, 1],
    'sfprev': [10, 1, 2, 3, 4, 5, 6, 8, 9],
    'sfnext': [2, 3, 4, 5, 6, 8, 9, 10, 1],
}
CH = 1 << 20


def load(dumpdir, prefix):
    fs = []
    for k in range(9):
        g = glob.glob(os.path.join(dumpdir, '%s%02d_f*_eeram.bin' % (prefix, k)))
        assert len(g) == 1, (prefix, k, g)
        fs.append(g[0])
    return [np.memmap(f, dtype=np.uint8, mode='r') for f in fs]


def main():
    dumpdir = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else 'sf_row'
    maps = load(dumpdir, prefix)
    n = len(maps[0])
    print('EE RAM = %d B' % n)
    hits_i, hits_f, hits_b = [], [], []
    for base in range(0, n, CH * 4):
        end = min(n, base + CH * 4)
        raw = [np.asarray(m[base:end], dtype=np.uint8).tobytes() for m in maps]
        st = np.stack([np.frombuffer(r, dtype='<u4').astype(np.int64) for r in raw])
        # u32 整数
        lo, hi = st.min(axis=0), st.max(axis=0)
        cand = np.nonzero((hi < 4096) & ((hi - lo) >= 4))[0]
        for c in cand:
            v = st[:, c].tolist()
            h = next((k for k, e in HYPS.items() if v == e), '')
            if h:
                hits_i.append((base + int(c) * 4, v, h))
        # float32
        u = (st & 0xFFFFFFFF).astype(np.uint32)
        fl = u.view(np.float32).astype(np.float64)
        fin = np.isfinite(fl).all(axis=0)
        cand = np.nonzero(fin & (np.abs(fl).max(axis=0) < 4096) & (fl.max(axis=0) - fl.min(axis=0) >= 4))[0]
        for c in cand:
            v = fl[:, c].tolist()
            h = next((k for k, e in HYPS.items()
                      if all(abs(v[i] - e[i]) < 1e-4 for i in range(9))), '')
            if h:
                hits_f.append((base + int(c) * 4, v, h))
        # u8 低字节
        b = (st & 0xFF)
        cand = np.nonzero((b.max(axis=0) < 32) & ((b.max(axis=0) - b.min(axis=0)) >= 4))[0]
        for c in cand:
            v = b[:, c].tolist()
            h = next((k for k, e in HYPS.items() if v == e), '')
            if h:
                hits_b.append((base + int(c) * 4, v, h))
    print('\n★ u32 整数命中 %d 个:' % len(hits_i))
    for a, v, h in hits_i:
        print('   %08X  %s  %s' % (a, v, h))
    print('★ float32 命中 %d 个:' % len(hits_f))
    for a, v, h in hits_f:
        print('   %08X  %s  %s' % (a, ['%.3f' % x for x in v], h))
    print('★ u8 低字节命中 %d 个:' % len(hits_b))
    for a, v, h in hits_b:
        print('   %08X  %s  %s' % (a, v, h))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
