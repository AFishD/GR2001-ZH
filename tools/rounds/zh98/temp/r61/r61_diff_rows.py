# -*- coding: utf-8 -*-
r"""r61_diff_rows.py — 差分找"当前选中行"变量 (round61 第 1 步)

输入: r61_recon.py 在**同一行上**各 dump 的全 EE RAM (`row00..row08_f*_eeram.bin`)。
      采样点 k 对应的 1-based 行号 = [1,2,3,4,5,6,8,9,10] (第 7 行「专家」是灰条, 光标跳过)。

判据: 找出所有"随选中行单调变化且值域很小"的地址 —— 计时器/动画计数器的步长是
      ~500 (采样间隔), 会被 "值域 < 32" 这条直接滤掉。

输出: 候选地址 + 值序列 + 匹配到的假设 (H1 0-based / H2 1-based / H3 可选项序号)。

用法: python work/builds/GR_ZH98/temp/r61/r61_diff_rows.py <dumpdir>
"""
import glob
import json
import os
import re
import sys

import numpy as np

HYP = {
    # ★ 实测行序 (r61_rows_sheet.png 逐行肉眼确认 —— 本轮采样落在**主菜单**, 不是特别收录列表):
    #   主菜单 9 项 = 训练/战术演习/战役/[快速任务·灰条]/多人游戏/统计/特别收录/选项/制作组
    #   row00 = up×9 之后 = 制作组(#9); 之后 8 次 down: #9→#1→#2→#3→#5→#6→#7→#8→#9
    'H_menu0': [8, 0, 1, 2, 4, 5, 6, 7, 8],      # 0-based 列表下标 (灰条 #4 被跳过)
    'H_menu1': [9, 1, 2, 3, 5, 6, 7, 8, 9],      # 1-based 列表序号
    'H_ord': [7, 0, 1, 2, 3, 4, 5, 6, 7],        # 可选行序号 (忽略灰条)
    'H_rev': [0, 8, 7, 6, 4, 3, 2, 1, 0],        # 反向
    # ---- 特别收录列表 (10 项, 第 7 项「专家」是灰条; 采样从第 1 行起 8 次 down) ----
    'H_sf0': [0, 1, 2, 3, 4, 5, 7, 8, 9],        # 0-based 列表下标
    'H_sf1': [1, 2, 3, 4, 5, 6, 8, 9, 10],       # 1-based 列表序号
    'H_sford': [0, 1, 2, 3, 4, 5, 6, 7, 8],      # 可选行序号 (忽略灰条)
    'H_sfrev': [9, 8, 7, 5, 4, 3, 2, 1, 0],      # 反向
}
CHUNK = 1 << 22
VMAX = 64          # "小值" 上限 (采样间隔 1000 帧, 计时器/动画计数器会被这条滤掉)


def load_rows(dumpdir, prefix='row'):
    files = []
    for k in range(9):
        g = glob.glob(os.path.join(dumpdir, '%s%02d_f*_eeram.bin' % (prefix, k)))
        assert len(g) == 1, '%s%02d: 期望 1 个 dump, 实际 %d' % (prefix, k, len(g))
        files.append(g[0])
    return files


def _candidates(blk, base, stride, exp, hits):
    """blk = (9, L) int64; 找出"9 个采样点上都是小值、且有足够多不同值"的列。"""
    lo, hi = blk.min(axis=0), blk.max(axis=0)
    cand = np.nonzero((hi < VMAX) & ((hi - lo) >= 4))[0]
    for c in cand:
        v = blk[:, c]
        vals = v.tolist()
        if len(set(vals)) < 5:          # 值太单调 ⇒ 多半是别的计数
            continue
        hyp = next((h for h, e in exp.items() if np.array_equal(v, e)), '')
        hits.append((base + int(c) * stride, vals, hyp))


def scan(dumpdir, prefix='row'):
    files = load_rows(dumpdir, prefix)
    print('采样文件 (%d 个):' % len(files))
    frames = []
    for f in files:
        m = re.search(r'_f(\d+)_', os.path.basename(f))
        frames.append(int(m.group(1)))
        print('   %-46s %d B  frame=%s' % (os.path.basename(f), os.path.getsize(f), m.group(1)))
    maps = [np.memmap(f, dtype=np.uint8, mode='r') for f in files]
    n = len(maps[0])
    for m in maps:
        assert len(m) == n, 'dump 长度不一致'
    print('EE RAM = %d B' % n)
    exp = {k: np.array(v, dtype=np.int64) for k, v in HYP.items()}

    hits_u8, hits_u32 = [], []
    for base in range(0, n, CHUNK):
        end = min(n, base + CHUNK)
        blk = np.stack([np.asarray(m[base:end], dtype=np.int64) for m in maps])  # (9, L)
        _candidates(blk, base, 1, exp, hits_u8)
        a = base - (base % 4)
        blk32 = np.stack([np.frombuffer(np.asarray(m[a:end], dtype=np.uint8).tobytes(),
                                        dtype='<u4').astype(np.int64) for m in maps])
        _candidates(blk32, a, 4, exp, hits_u32)
    return frames, hits_u8, hits_u32


def main():
    dumpdir = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else 'row'
    frames, h8, h32 = scan(dumpdir, prefix)
    print('\n采样帧号 = %s' % frames)
    print('假设表: %s' % json.dumps(HYP))
    for name, hits in (('u8', h8), ('u32', h32)):
        exact = [h for h in hits if h[2]]
        other = [h for h in hits if not h[2]]
        print('\n===== %s 候选: 共 %d 个 (精确命中假设 %d 个) =====' % (name, len(hits), len(exact)))
        for addr, vals, hyp in exact:
            print('  ★ %08X  %s   %s' % (addr, vals, hyp))
        print('  --- 其它"单调小值"候选 (前 40) ---')
        for addr, vals, _ in other[:40]:
            print('    %08X  %s' % (addr, vals))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
