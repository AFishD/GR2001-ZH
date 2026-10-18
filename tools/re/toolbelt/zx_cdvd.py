# -*- coding: utf-8 -*-
r"""zx_cdvd.py — 解析 gsrunner 的 cdvd.log, 统计 **COMMON.PAK 字库像素区**的读取量

cdvd.log 每行 = `<frame> <lsn>`（GRResearch.cpp::LogCdvdRead, lsn = 2048 B 扇区号）。
本工具把 lsn 映射回 ISO 绝对字节, 与给定区间求交, 给三种口径:
  · 事件数 (行数) / 去重 lsn 数 / 去重后覆盖字节数 / 求交后覆盖字节数
用法: python zx_cdvd.py <cdvd.log> [<cdvd.log2> ...] --region <abs_off> <len> [--label X]
"""
import argparse
import os
import sys

SEC = 2048
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(path):
    ev = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            p = ln.split()
            if len(p) != 2:
                continue
            try:
                ev.append((int(p[0]), int(p[1])))
            except ValueError:
                continue
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--region', nargs=2, type=lambda s: int(s, 0), required=True,
                    metavar=('ABS_OFF', 'LEN'))
    ap.add_argument('--label', default='region')
    a = ap.parse_args()
    off, ln = a.region
    lo, hi = off // SEC, (off + ln + SEC - 1) // SEC
    print('区域 %s = ISO 0x%X..0x%X (%d B) ⇒ 扇区 %d..%d' % (a.label, off, off + ln, ln, lo, hi))
    for p in a.logs:
        ev = load(p)
        inreg = [(fr, l) for (fr, l) in ev if lo <= l < hi]
        lsns = sorted({l for (_f, l) in inreg})
        # 覆盖字节: 去重扇区 × 2048, 再与区域求交
        cov = len(lsns) * SEC
        inter = 0
        for l in lsns:
            s, e = l * SEC, l * SEC + SEC
            inter += max(0, min(e, off + ln) - max(s, off))
        print('  %-46s 事件 %6d ; 去重扇区 %5d ; 覆盖 %8d B ; 与区求交 %8d B'
              % (os.path.basename(os.path.dirname(p)) + '/' + os.path.basename(p),
                 len(inreg), len(lsns), cov, inter))
        print('       首/末事件 frame: %s' % (('%d' % inreg[0][0], '%d' % inreg[-1][0])
                                              if inreg else '-'))


if __name__ == '__main__':
    main()
