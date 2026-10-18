# -*- coding: utf-8 -*-
r"""r61_sf_probe.py — 定点找"特别收录列表当前选中行"变量。

第一轮差分 (r61_diff_rows.py) 在全 32MB EE RAM 上没找到精确命中"小整数行号"的地址,
说明特别收录列表的选中态**不是**一个独立的小整数全局量。两条更有针对性的路子:

  A. **邻域**: 主菜单的选中项在 0x013379D0 (UI 框架的全局块)。两个列表屏很可能由同一套
     UI 代码驱动 ⇒ 特别收录的选中态就在同一块里。扫 0x013379D0 附近 ±N KB, 列出所有
     "9 个采样点上不全相同"的 4 字节字, 直接看值序列。

  B. **全 RAM 的"9 值互不相同且都是小量"**: 覆盖"存的是下标/序号/小指针"的情形
     (放宽到 < 0x100000, 因为可能是指向小表的指针)。

用法: python work/builds/GR_ZH98/temp/r61/r61_sf_probe.py <dumpdir> [prefix] [window_kb]
"""
import glob
import os
import sys

import numpy as np

H_SF1 = [1, 2, 3, 4, 5, 6, 8, 9, 10]     # 1-based 行号 (实测, 灰条 #7 跳过)
H_SF0 = [0, 1, 2, 3, 4, 5, 7, 8, 9]
H_SFORD = [0, 1, 2, 3, 4, 5, 6, 7, 8]
HYPS = {'sf1': H_SF1, 'sf0': H_SF0, 'sford': H_SFORD,
        'sf1-1': [v - 1 for v in H_SF1], 'sf_prev': [9] + H_SF1[:8]}
MENU_ADDR = 0x013379D0


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
    win_kb = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    maps = load(dumpdir, prefix)
    n = len(maps[0])
    print('EE RAM = %d B; 采样 = %s' % (n, [os.path.basename(f) for f in glob.glob(
        os.path.join(dumpdir, '%s00_f*_eeram.bin' % prefix))]))

    # ---------- A. 主菜单变量邻域 ----------
    a = max(0, MENU_ADDR - win_kb * 1024) & ~3
    b = min(n, MENU_ADDR + win_kb * 1024)
    print('\n===== A. 邻域 0x%08X..0x%08X (±%d KB) 中"随行变化"的 4 字节字 =====' % (a, b, win_kb))
    blk = np.stack([np.frombuffer(np.asarray(m[a:b], dtype=np.uint8).tobytes(),
                                  dtype='<u4').astype(np.int64) for m in maps])
    diff = np.nonzero(blk.max(axis=0) != blk.min(axis=0))[0]
    print('  有变化的字 = %d / %d' % (len(diff), blk.shape[1]))
    exact = []
    for c in diff:
        v = blk[:, c].tolist()
        hyp = next((h for h, e in HYPS.items() if v == e), '')
        if hyp:
            exact.append((a + int(c) * 4, v, hyp))
    print('  ★ 命中假设的: %s' % (['%08X %s %s' % t for t in exact] or '无'))
    print('  --- 全部有变化的字 (值序列) ---')
    for c in diff:
        v = blk[:, c].tolist()
        print('    %08X  %s%s' % (a + int(c) * 4, v,
                                  '   <<< 含 1..10 类小值' if max(v) <= 16 else ''))

    # ---------- B. 全 RAM: 9 值互不相同且都是小量 ----------
    print('\n===== B. 全 RAM: 9 个采样点 u32 互不相同且都 < 0x100000 =====')
    hits = []
    CH = 1 << 22
    for base in range(0, n, CH):
        end = min(n, base + CH)
        st = np.stack([np.frombuffer(np.asarray(m[base:end], dtype=np.uint8).tobytes(),
                                     dtype='<u4').astype(np.int64) for m in maps])
        hi = st.max(axis=0)
        cand = np.nonzero(hi < 0x100000)[0]
        for c in cand:
            v = st[:, c]
            if len(set(v.tolist())) != 9:
                continue
            hits.append((base + int(c) * 4, v.tolist()))
    print('  候选 = %d 个' % len(hits))
    ex = [(ad, v, next((h for h, e in HYPS.items() if v == e), '')) for ad, v in hits]
    ex = [t for t in ex if t[2]]
    print('  ★ 命中假设的: %s' % (['%08X %s %s' % t for t in ex] or '无'))
    small = [(ad, v) for ad, v in hits if max(v) <= 64]
    print('  --- 值都 <=64 的候选 (%d 个) ---' % len(small))
    for ad, v in small[:60]:
        print('    %08X  %s' % (ad, v))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
