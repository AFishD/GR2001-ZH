# -*- coding: utf-8 -*-
r"""oomfix_ramdiff.py —— 比对同一 run 内两帧的 EE RAM 全量快照（`win_f%08u_eeram.bin`）。

用法:
  python oomfix_ramdiff.py <dirA> <frameA> <dirB|同> <frameB> [--json out.json]

输出:
  * 差分总字节数、涉及的 4 KB 页数
  * **低端重点区** 0x0000..0x0400 / 0x1000..0x1400 / 0x1300..0x1310 的逐字节结论
  * 前 N 个差分窗口（偏移 + 长度 + 首尾字节）
"""
import argparse
import json
import os
import sys

MAIN_RAM = 32 * 1024 * 1024
FOCUS = [(0x0000, 0x0400, '异常向量区 0x0..0x400'),
         (0x0000, 0x0300, '异常向量区 0x0..0x300（任务书判据）'),
         (0x1000, 0x1400, '低端 0x1000..0x1400'),
         (0x1300, 0x1310, '0x1300 头部 16 B（任务书判据）'),
         (0x1300, 0x1400, '0x1300..0x1400')]


def path(d, fr):
    return os.path.join(d, 'win_f%08u_eeram.bin' % fr)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('dirA')
    ap.add_argument('frameA', type=int)
    ap.add_argument('dirB')
    ap.add_argument('frameB', type=int)
    ap.add_argument('--json', default=None)
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--detail', default=None, help='额外打印该十六进制地址起 64 B 的两侧内容')
    a = ap.parse_args()

    pa, pb = path(a.dirA, a.frameA), path(a.dirB, a.frameB)
    A = open(pa, 'rb').read()
    B = open(pb, 'rb').read()
    assert len(A) == len(B) == MAIN_RAM, (len(A), len(B))
    rep = dict(A=dict(dir=os.path.abspath(a.dirA), frame=a.frameA),
               B=dict(dir=os.path.abspath(a.dirB), frame=a.frameB))
    # 差分 run
    runs = []
    i = 0
    while i < MAIN_RAM:
        if A[i] != B[i]:
            j = i
            while j < MAIN_RAM and (j - i) < 4096 and A[j] != B[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    total = sum(n for _o, n in runs)
    pages = set(o >> 12 for o, n in runs for o in range(o, o + n, 4096))
    rep['diff_bytes'] = total
    rep['diff_runs'] = len(runs)
    rep['diff_pages_4k'] = len(pages)
    rep['runs_head'] = [dict(off='0x%06X' % o, len=n) for (o, n) in runs[:a.top]]

    print('A = %s frame %d' % (rep['A']['dir'], a.frameA))
    print('B = %s frame %d' % (rep['B']['dir'], a.frameB))
    print('EE RAM 差分：%d 字节 / %d 个连续段 / %d 个 4 KB 页'
          % (total, len(runs), len(pages)))
    focus = []
    for (lo, hi, why) in FOCUS:
        n = sum(1 for k in range(lo, hi) if A[k] != B[k])
        first = next((k for k in range(lo, hi) if A[k] != B[k]), None)
        focus.append(dict(lo='0x%04X' % lo, hi='0x%04X' % hi, why=why, diff_bytes=n,
                          first_off=None if first is None else '0x%06X' % first,
                          first_A=None if first is None else '%02X' % A[first],
                          first_B=None if first is None else '%02X' % B[first]))
        print('   %-34s 差分 %5d B  首差 %s (%s -> %s)'
              % (why, n, focus[-1]['first_off'], focus[-1]['first_A'], focus[-1]['first_B']))
    rep['focus'] = focus
    if a.detail:
        d = int(a.detail, 16)
        print('   0x%06X A: %s' % (d, A[d:d + 64].hex()))
        print('   0x%06X B: %s' % (d, B[d:d + 64].hex()))
    print('   差分段（前 %d）: %s' % (a.top, ', '.join('%s+%d' % (r['off'], r['len'])
                                                     for r in rep['runs_head'])))
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[json] %s' % a.json)


if __name__ == '__main__':
    main()
