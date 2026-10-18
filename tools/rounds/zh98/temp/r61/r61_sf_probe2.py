# -*- coding: utf-8 -*-
r"""r61_sf_probe2.py — 换两种"选中态"表示去找特别收录列表的当前行。

r61_diff_rows / r61_sf_probe 已经排除了"一个独立的小整数行号全局量"。剩下两种常见写法:

  P1. **每项一个标志位** (UI 最常用的做法): 第 k 个采样点上, 恰好"选中项对象"的某个字段
      是 1, 其余 8 个采样点上同一字段是 0。⇒ 特征是"9 个值里 8 个相同、1 个是异类",
      且**异类落在哪个采样点**刚好把 9 个采样点各覆盖一次。
  P2. **高亮条的坐标是浮点数** (金带 y 随行移动): 9 个值互不相同、按 float32 解释后单调,
      步长近似常数 (实测金带 y = 83/111/138/165/193/220/275/302/329)。

判据: P1 找出 9 个地址 (每个对应一行), 或 P2 找出 1 个地址 (y 坐标)。

用法: python work/builds/GR_ZH98/temp/r61/r61_sf_probe2.py <dumpdir> [prefix]
"""
import glob
import os
import sys

import numpy as np

CH = 1 << 19          # 每次 512K 个 u32 = 2 MB
GOLD_Y = [83.0, 111.0, 138.0, 165.0, 193.0, 220.0, 275.0, 302.0, 329.0]


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

    p1 = {k: [] for k in range(9)}      # 异类落在采样 k
    p2 = []
    for base in range(0, n, CH * 4):
        end = min(n, base + CH * 4)
        raw = [np.asarray(m[base:end], dtype=np.uint8).tobytes() for m in maps]
        st = np.stack([np.frombuffer(r, dtype='<u4').astype(np.int64) for r in raw])
        mn = st.min(axis=0)
        mx = st.max(axis=0)
        neq = mn != mx
        # ---- P1: 8 个相同 + 1 个异类 ----
        if neq.any():
            cnt_min = (st == mn).sum(axis=0)
            cnt_max = (st == mx).sum(axis=0)
            out_max = neq & (cnt_min == 8)          # 异类是最大值
            out_min = neq & (cnt_max == 8)          # 异类是最小值
            for mask, pick in ((out_max, st.argmax(axis=0)), (out_min, st.argmin(axis=0))):
                for c in np.nonzero(mask)[0]:
                    k = int(pick[c])
                    p1[k].append((base + int(c) * 4, st[:, c].tolist()))
        # ---- P2: float32 单调 (步长近似常数) ----
        fl = st.astype(np.uint32).view(np.float32).astype(np.float64)
        d = np.diff(fl, axis=0)
        ok = (np.abs(d - d[0:1]).max(axis=0) < 2.0) & (d[0] != 0) & np.isfinite(fl).all(axis=0)
        for c in np.nonzero(ok)[0]:
            p2.append((base + int(c) * 4, fl[:, c].tolist()))

    print('\n===== P1. "8 同 1 异" 且异类覆盖 9 个采样点 =====')
    tot = 0
    for k in range(9):
        cands = p1[k]
        tot += len(cands)
        small = [(a, v) for a, v in cands if max(v) <= 8 and min(v) == 0]
        print('  采样 #%d (第 %d 行): 异类候选 %d 个; 其中"0/1 型" %d 个 %s'
              % (k, k + 1, len(cands), len(small),
                 ['%08X %s' % t for t in small[:6]]))
    print('  合计 %d 个' % tot)

    print('\n===== P2. float32 等步长单调 (高亮条 y 之类) =====')
    print('  候选 = %d 个' % len(p2))
    for a, v in p2[:30]:
        mark = ''
        if len(v) == 9 and max(abs(v[i] - GOLD_Y[i]) for i in range(9)) < 1.5:
            mark = '   <<<<<< 与实测金带 y 完全一致!'
        print('    %08X  %s%s' % (a, ['%.2f' % x for x in v], mark))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
