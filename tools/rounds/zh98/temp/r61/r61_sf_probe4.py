# -*- coding: utf-8 -*-
r"""r61_sf_probe4.py — 在 **IOP RAM** 里找特别收录列表的当前行 (EE RAM 已排除标量下标)。

r61_sf_probe3 已证明: EE 主存里**没有**任何 1/2/4 字节的标量按行号变化 (u32/float32/u8
三种解释都试过)。P1 显示表示法是"**每项一个选中标志位**"(0x0091E7F8..0x00920988, 相邻项
相差 ~0x410, 跳过灰条那一步正好跨 0x860)。
本脚本补最后一块: live `dump` 命令同时落了 IOP RAM (2 MB), 扫一遍同样三种解释。

用法: python work/builds/GR_ZH98/temp/r61/r61_sf_probe4.py <dumpdir> [prefix]
"""
import glob
import os
import sys

import numpy as np

HYPS = {
    'sf1': [1, 2, 3, 4, 5, 6, 8, 9, 10],
    'sf0': [0, 1, 2, 3, 4, 5, 7, 8, 9],
    'sford': [0, 1, 2, 3, 4, 5, 6, 7, 8],
    'sfrev': [10, 9, 8, 6, 5, 4, 3, 2, 1],
    'sfprev': [10, 1, 2, 3, 4, 5, 6, 8, 9],
}


def main():
    dumpdir = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else 'sf_row'
    fs = []
    for k in range(9):
        g = glob.glob(os.path.join(dumpdir, '%s%02d_f*_iopram.bin' % (prefix, k)))
        assert len(g) == 1, (prefix, k, g)
        fs.append(g[0])
    maps = [np.memmap(f, dtype=np.uint8, mode='r') for f in fs]
    n = len(maps[0])
    print('IOP RAM = %d B; 采样 9 份' % n)
    raw = [np.asarray(m, dtype=np.uint8).tobytes() for m in maps]
    st = np.stack([np.frombuffer(r, dtype='<u4').astype(np.int64) for r in raw])
    hits = []
    lo, hi = st.min(axis=0), st.max(axis=0)
    for c in np.nonzero((hi < 4096) & ((hi - lo) >= 4))[0]:
        v = st[:, c].tolist()
        h = next((k for k, e in HYPS.items() if v == e), '')
        if h:
            hits.append(('u32', int(c) * 4, v, h))
    u = (st & 0xFFFFFFFF).astype(np.uint32)
    fl = u.view(np.float32).astype(np.float64)
    fin = np.isfinite(fl).all(axis=0)
    for c in np.nonzero(fin & (np.abs(fl).max(axis=0) < 4096)
                        & (fl.max(axis=0) - fl.min(axis=0) >= 4))[0]:
        v = fl[:, c].tolist()
        h = next((k for k, e in HYPS.items()
                  if all(abs(v[i] - e[i]) < 1e-4 for i in range(9))), '')
        if h:
            hits.append(('f32', int(c) * 4, v, h))
    b = st & 0xFF
    for c in np.nonzero((b.max(axis=0) < 32) & ((b.max(axis=0) - b.min(axis=0)) >= 4))[0]:
        v = b[:, c].tolist()
        h = next((k for k, e in HYPS.items() if v == e), '')
        if h:
            hits.append(('u8', int(c) * 4, v, h))
    print('★ IOP RAM 命中 %d 个:' % len(hits))
    for t, a, v, h in hits:
        print('   %s %08X  %s  %s' % (t, a, v, h))
    # 顺带: IOP 里"8 同 1 异"且覆盖 9 个采样点的 0/1 型标志
    mn, mx = st.min(axis=0), st.max(axis=0)
    neq = mn != mx
    cov = {k: [] for k in range(9)}
    for c in np.nonzero(neq & ((st == mn).sum(axis=0) == 8))[0]:
        v = st[:, c].tolist()
        if max(v) <= 4 and min(v) == 0:
            cov[v.index(max(v))].append((int(c) * 4, v))
    print('\nIOP "0/1 型 8同1异" 覆盖情况: %s'
          % {k: len(v) for k, v in cov.items()})
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
