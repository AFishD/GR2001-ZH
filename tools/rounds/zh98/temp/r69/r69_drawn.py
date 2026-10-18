# -*- coding: utf-8 -*-
r"""r69_drawn.py — 从 drawlog 抽出**实际绘制的字符串序列**, 与 CSV 手调断句逐行对照。

口径: `PC=219EB0` = DrawString(每行文本各一次), 行尾 `| ` 后是原始字节 (码表解码)。
只看一帧: 取该帧内 (RA, THIS) 相同的连续一段 —— 介绍框的每一行都来自同一个组件的同一条路径。

用法: python r69_drawn.py <drawlog> <version_text_long.csv> <SFXML:T0xxx> [--frame N]
"""
import argparse
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, 'tools', 'capture')):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'capture'))
import nav_hook as N                                                    # noqa: E402

RX = re.compile(r'F(\d+) PC=219EB0 RA=(\w+) THIS=(\w+)')


def width(s):
    return sum((3 if c == ' ' else (8 if 0x21 <= ord(c) <= 0x7E else 16)) + 1 for c in s.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('drawlog')
    ap.add_argument('csv')
    ap.add_argument('entry')
    ap.add_argument('--frame', type=int, default=None)
    ap.add_argument('--width', type=int, default=60)
    a = ap.parse_args()

    rows = list(csv.reader(io.open(a.csv, encoding='utf-8-sig', newline='')))
    hdr = rows[0]
    ie, ii = hdr.index('text_edited'), hdr.index('id')
    want = [r for r in rows[1:] if r[ii] == a.entry]
    assert want, a.entry
    exp = [l for l in want[0][ie].replace('{Warp}', '\n').split('\n')]

    drawn = {}
    for ln in io.open(a.drawlog, encoding='utf-8', errors='replace'):
        m = RX.search(ln)
        if not m:
            continue
        fr = int(m.group(1))
        if a.frame is not None and fr != a.frame:
            continue
        raw = b''
        if '|' in ln:
            try:
                raw = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:96])
            except Exception:                                           # noqa: BLE001
                continue
        t = N.dec_bytes(raw)
        if t:
            drawn.setdefault(fr, []).append((m.group(2), m.group(3), t))

    if not drawn:
        print('该 drawlog 里没有可解码的 219EB0 行'); return 1
    fr = a.frame if a.frame in drawn else max(drawn)
    seq = drawn[fr]
    print('帧 F%d : 可解码绘制串 %d 条' % (fr, len(seq)))
    # drawlog 的串是"从固定偏移起 96 字节", 会把后面几条拼在一起 ⇒ 用**前缀匹配**
    exp_set = [e.strip() for e in exp if e.strip()]
    hit = []
    for ra, th, t in seq:
        if ra not in ('21CA00', '21C62C', '21C85C', '21C8B0'):
            continue        # 只看 RSHTML/RSTextComponent 的正文绘制路径
        ts = t
        for e in exp_set:
            if ts.startswith(e):
                hit.append((ra, e))
                break
    print('\n★ 在介绍框绘制路径 (RA∈{21CA00,21C62C,21C85C,21C8B0}) 上, '
          '与 CSV 手调断句**逐字前缀相同**的绘制 %d 条:' % len(hit))
    for i, (ra, e) in enumerate(hit):
        print('   %-3d %-7s w=%-4d %s' % (i, ra, width(e), e[:a.width]))
    exp_used = [e for _ra, e in hit]
    print('\n与 CSV 前 %d 行的顺序一致性: %s' % (len(hit),
          '✓ 完全一致' if exp_used == exp_set[:len(exp_used)] else '✗ 有出入'))
    print('\nCSV 手调断句 (前 %d 行):' % min(len(exp_set), 16))
    for j, e in enumerate(exp_set[:16]):
        print('   %-3d %-4d %s' % (j, width(e), e[:a.width]))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
