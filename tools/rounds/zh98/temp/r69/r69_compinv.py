# -*- coding: utf-8 -*-
r"""r69_compinv.py — 扫所有 drawlog 的 `PC=21C4C0` 文本组件钩子行, 汇总 (W,H) 清单。

用途: 找出"简报正文组件"的宽度 —— 只要历史上有任何一次跑批到过简报页,
      它的 W 就会作为新的 (W,H) 组合出现, 并带着帧区间。

用法: python r69_compinv.py [--glob 子串] [--minw N]
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, 'work', 'builds')):
    REPO = os.path.dirname(REPO)

RX = re.compile(r'F(\d+) PC=21C4C0 COMP=(\w+) font=(\w+) style=(\w+) ax=(-?\d+) ay=(-?\d+) '
                r'W=(-?\d+) H=(-?\d+)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minw', type=int, default=0)
    a = ap.parse_args()
    logs = sorted(glob.glob(os.path.join(REPO, 'work', '**', 'drawlog.txt'), recursive=True))
    logs = [p for p in logs if os.path.getsize(p) > 1000]
    print('扫 %d 份 drawlog' % len(logs))
    inv = {}
    for p in logs:
        tag = os.path.relpath(p, REPO)
        n = 0
        try:
            for ln in io.open(p, encoding='utf-8', errors='replace'):
                m = RX.search(ln)
                if not m:
                    continue
                n += 1
                w, h = int(m.group(7)), int(m.group(8))
                fr = int(m.group(1))
                k = (w, h)
                d = inv.setdefault(k, {'n': 0, 'files': {}, 'fmin': fr, 'fmax': fr,
                                       'ay': set(), 'style': set()})
                d['n'] += 1
                d['files'][tag] = d['files'].get(tag, 0) + 1
                d['fmin'] = min(d['fmin'], fr)
                d['fmax'] = max(d['fmax'], fr)
                d['ay'].add(int(m.group(6)))
                d['style'].add(m.group(4))
        except Exception as e:                                          # noqa: BLE001
            print('  !! %s: %s' % (tag, e))
        print('  %-58s 21C4C0 行 = %d' % (tag, n))
    print('\n===== (W,H) 清单 (%d 组) =====' % len(inv))
    rows = sorted(inv.items(), key=lambda kv: -kv[1]['n'])
    print('%-14s %10s %10s %-22s %s' % ('(W,H)', '行数', '帧区间', 'ay 值(前6)', '出现过的 drawlog'))
    for (w, h), d in rows:
        if w < a.minw:
            continue
        print('%-14s %10d %5d..%-6d %-22s %s'
              % ('(%d,%d)' % (w, h), d['n'], d['fmin'], d['fmax'],
                 ','.join(str(x) for x in sorted(d['ay'])[:6]),
                 '; '.join('%s×%d' % (k.split(os.sep)[-3], v)
                           for k, v in sorted(d['files'].items())[:4])))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
