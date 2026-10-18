# -*- coding: utf-8 -*-
r"""ab_clusters.py — 从 ab_diff.json 里取出指定帧的差异像素, 按邻近聚类并打印,
用来决定"裁哪一块"做对照图。

用法: python ab_clusters.py <ab_diff.json> <frame1,frame2,...> [--gap 6]
"""
import io
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    p = sys.argv[1]
    want = [x.strip() for x in sys.argv[2].split(',')]
    gap = int(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 6
    d = json.load(io.open(p, encoding='utf-8'))
    by = {r['frame']: r for r in d['detail'] if 'px' in r}
    for f in want:
        if f not in by:
            print('%s: 无差异或不在 json 里' % f)
            continue
        px = [tuple(q) for q in by[f]['px']]
        print('=' * 80)
        print('%s  差异 %d 像素 (json 记录 %d)' % (f, by[f]['n'], len(px)))
        # 按 y 聚类
        px.sort()
        cl = []
        cur = [px[0]]
        for q in px[1:]:
            if q[0] - cur[-1][0] <= gap:
                cur.append(q)
            else:
                cl.append(cur)
                cur = [q]
        cl.append(cur)
        for c in cl:
            ys = [q[0] for q in c]
            xs = [q[1] for q in c]
            print('  簇: y=%d..%d x=%d..%d  n=%d  像素=%s'
                  % (min(ys), max(ys), min(xs), max(xs), len(c),
                     [(y, x) for y, x in c][:24]))


if __name__ == '__main__':
    main()
