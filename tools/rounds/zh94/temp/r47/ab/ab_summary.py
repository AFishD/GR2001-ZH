# -*- coding: utf-8 -*-
r"""ab_summary.py — 把 ab_diff.json 汇总成报告用的数字。

输出:
  · 相同帧/差异帧/差异像素总数;
  · 差异像素出现在哪些 y 行 (预期: 只出现在"受影响字底部那一行"对应的少数几个 y);
  · 每个 y 行的像素数;
  · 逐帧差异像素数分布 (min/中位/max)。
"""
import io
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    d = json.load(io.open(sys.argv[1], encoding='utf-8'))
    recs = [r for r in d['detail'] if 'px' in r]
    tot = sum(r['n'] for r in recs)
    ys = {}
    for r in recs:
        for (y, x) in r['px']:
            ys.setdefault(y, 0)
            ys[y] += 1
    ns = sorted(r['n'] for r in recs)
    print('帧: 同名 %d; 逐像素相同 %d; 有差异 %d'
          % (d['frames_common'], d['frames_same'], d['frames_diff']))
    print('差异像素总计 %d (逐帧 %d..%d, 中位 %d)'
          % (tot, ns[0], ns[-1], ns[len(ns) // 2]))
    print('差异像素出现在 %d 个不同的 y 行:' % len(ys))
    for y in sorted(ys):
        print('   y=%3d : %3d px' % (y, ys[y]))
    # 每帧差异簇数
    print()
    print('每帧差异像素数 (前 20 帧): %s' % [r['n'] for r in recs[:20]])
    print('包围盒高度取值: %s' % sorted(set(r['h'] for r in recs)))


if __name__ == '__main__':
    main()
