# -*- coding: utf-8 -*-
r"""thr_summary.py -- round86 全部实机盘结果汇总表

用法: python tools/re/toolbelt/thr_summary.py
"""
import glob
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
T = os.path.join(REPO, 'work', 'builds', 'GR_THR86', 'temp')

RUNS = [
    ('base  GR_ZH124 (对照)', 'dump_base', r'work\builds\GR_ZH124\GR_ZH124.iso'),
    ('h513 skipreal  (+560)', 'dump_h513', r'work\builds\GR_THR86\GR_THR86_h513.iso'),
    ('h513 real-fixed(+560)', 'dump_h513_real', r'work\builds\GR_THR86\GR_THR86_h513_real.iso'),
    ('h512 旧px规则  (+384)', 'dump_h512', r'work\builds\GR_THR86\GR_THR86_h512.iso'),
    ('h640 skipreal(+65536)', 'dump_h640_skip', r'work\builds\GR_THR86\GR_THR86_h640_skipreal.iso'),
    ('h640 旧px规则(+66016)', 'dump_h640', r'work\builds\GR_THR86\GR_THR86_h640.iso'),
    ('w2048 旧px规则(+262912)', 'dump_w2048', r'work\builds\GR_THR86\GR_THR86_w2048.iso'),
    ('v2 h513  (+512)', 'dump_v2_h513', r'work\builds\GR_THR86\v2_h513.iso'),
    ('v2 h514  (+1024)', 'dump_v2_h514', r'work\builds\GR_THR86\v2_h514.iso'),
    ('v2 h515  (+1536)', 'dump_v2_h515', r'work\builds\GR_THR86\v2_h515.iso'),
    ('v2 h516  (+2048)', 'dump_v2_h516', r'work\builds\GR_THR86\v2_h516.iso'),
    ('v2 h520  (+4096)', 'dump_v2_h520', r'work\builds\GR_THR86\v2_h520.iso'),
    ('v2 h576  (+32768)', 'dump_v2_h576', r'work\builds\GR_THR86\v2_h576.iso'),
    ('v2 h640  (+65536)', 'dump_v2_h640', r'work\builds\GR_THR86\v2_h640.iso'),
    ('v2 h640 +ISO/IMG 加长', 'dump_v2_h640_grown', r'work\builds\GR_THR86\v2_h640_grown.iso'),
    ('v2 h644', 'dump_v2_h644', r'work\builds\GR_THR86\v2_h644.iso'),
    ('v2 h672', 'dump_v2_h672', r'work\builds\GR_THR86\v2_h672.iso'),
    ('v2 h704', 'dump_v2_h704', r'work\builds\GR_THR86\v2_h704.iso'),
    ('v2 h764', 'dump_v2_h764', r'work\builds\GR_THR86\v2_h764.iso'),
    ('v2 h768', 'dump_v2_h768', r'work\builds\GR_THR86\v2_h768.iso'),
    ('v2 h832', 'dump_v2_h832', r'work\builds\GR_THR86\v2_h832.iso'),
    ('v2 h1020', 'dump_v2_h1020', r'work\builds\GR_THR86\v2_h1020.iso'),
    ('v2 h1024 (16 段)', 'dump_v2_h1024', r'work\builds\GR_THR86\v2_h1024.iso'),
    ('v2 h1024 (8 段,64K/段)', 'dump_v2_h1024_s64k', r'work\builds\GR_THR86\v2_h1024_s64k.iso'),
    ('v2 w2048 (+262144)', 'dump_v2_w2048', r'work\builds\GR_THR86\v2_w2048.iso'),
]


def shots(d):
    return {os.path.basename(p): hashlib.sha256(open(p, 'rb').read()).hexdigest()
            for p in sorted(glob.glob(os.path.join(d, 'snap_*.png')))}


def cdvd(p):
    fr = set()
    n = 0
    mx = 0
    last = 0
    with open(p, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            a = line.strip().split()
            if len(a) < 2:
                continue
            n += 1
            fr.add(int(a[0]))
            mx = max(mx, int(a[1]))
            last = max(last, int(a[1])) if int(a[0]) == max(fr) else last
    return n, (min(fr) if fr else -1), (max(fr) if fr else -1), mx


def main():
    base = shots(os.path.join(T, 'dump_base'))
    print('=' * 118)
    print('%-24s %5s %6s %6s %8s %8s %8s %8s %10s %s'
          % ('盘', 'PNG', '画面数', '=对照', '读事件', 'f0', 'f1', 'maxLBA', 'newfont', '判定'))
    print('-' * 118)
    for (label, sub, iso) in RUNS:
        d = os.path.join(T, sub)
        if not os.path.isdir(d):
            print('%-24s (无 dump)' % label)
            continue
        s = shots(d)
        uniq = len(set(s.values()))
        same = sum(1 for k in base if k in s and base[k] == s[k])
        n, f0, f1, mx = cdvd(os.path.join(d, 'cdvd.log'))
        gl = os.path.join(d, 'grlog.txt')
        nf = '-'
        if os.path.isfile(gl):
            txt = open(gl, encoding='utf-8', errors='replace').read()
            m = re.search(r"needle 'newfontrevisedrs': (\d+) hits", txt)
            nf = m.group(1) if m else '?'
        verdict = 'PASS(与对照同构)' if (len(s) == len(base) and uniq > 20 and same >= 100) \
            else ('滞后-卡同一画面' if uniq <= 3 else '?')
        print('%-24s %5d %6d %6d %8d %8d %8d %8d %10s %s'
              % (label, len(s), uniq, same, n, f0, f1, mx, nf, verdict))
    print('-' * 118)
    print("判据: PNG 张数 / 画面数(不同 sha256 的截图数) / 与对照逐字节相同的截图数 / cdvd 读流。")
    print("      '画面数=1' = 全程同一画面(卡死); 对照与通过盘 画面数 161~164。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
