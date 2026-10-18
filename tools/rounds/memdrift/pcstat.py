# -*- coding: utf-8 -*-
r"""pcstat.py — 分析 pcsample.txt ("<frame> <cpuRegs.pc>", 每 4 帧一行) 判断是否卡死

判据
----
正常游玩: PC 分布很宽 (数千个不同 PC), 最长"同一 PC 连续出现"很短 (< ~50 行 = <200 帧)。
卡死 (EE 陷在紧循环里): distinct PC 塌缩到 1~3 个, 且出现极长的连续游程。
用户的实机 log 就是后者的极端形态 (两个 PC 交替: 0x001024D0 / 0x00102584)。
"""
import argparse
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--tail', type=float, default=0.05, help='"尾段"占比')
    a = ap.parse_args()
    rows = []
    with open(a.path, encoding='utf-8', errors='replace') as fh:
        for ln in fh:
            q = ln.split()
            if len(q) == 2:
                rows.append((int(q[0]), int(q[1], 16)))
    if not rows:
        sys.exit('空文件')
    print('样本 %d 行 ; 帧 %d..%d (每 4 帧一个样本)' % (len(rows), rows[0][0], rows[-1][0]))
    allpc = {pc for (_f, pc) in rows}
    print('★ 全段 distinct PC = %d' % len(allpc))
    for frac, name in ((1.0, '全段'), (0.25, '后 25%'), (0.05, '后 5%'), (0.01, '后 1%')):
        seg = rows[int(len(rows) * (1 - frac)):]
        d = {pc for (_f, pc) in seg}
        print('  %-7s 帧 %d..%d : distinct PC = %-6d' % (name, seg[0][0], seg[-1][0], len(d)))
    # 最长同一 PC 游程 / 最长 ≤2 PC 游程 / 最长 ≤3 PC 游程
    def runmax(k):
        best = cur = 1
        win = [rows[0][1]]
        for i in range(1, len(rows)):
            win.append(rows[i][1])
            if len(win) > 64:
                win.pop(0)
            if len(set(win[-k:])) <= k:
                cur += 1
                best = max(best, cur)
            else:
                cur = 1
        return best
    for k in (1, 2, 3, 8):
        r = runmax(k)
        print('  最长"最近 ≤%d 个不同 PC"游程 = %d 行 (= %d 帧)' % (k, r, r * 4))
    print('\n后 1%% 热点 PC:')
    seg = rows[int(len(rows) * 0.99):]
    for pc, n in Counter(pc for (_f, pc) in seg).most_common(12):
        print('    %08X  %d 次' % (pc, n))
    print('\n全段 top 12 PC:')
    for pc, n in Counter(pc for (_f, pc) in rows).most_common(12):
        print('    %08X  %d 次 (%.3f%%)' % (pc, n, 100.0 * n / len(rows)))
    # 用户实机那两个 PC 有没有出现
    for tgt in (0x001024D0, 0x00102584):
        print('  用户实机卡死 PC %08X 出现 %d 次' % (tgt, sum(1 for (_f, pc) in rows if pc == tgt)))


if __name__ == '__main__':
    main()
