# -*- coding: utf-8 -*-
r"""r69_lineaudit.py — 「特别收录」SFXML 逐行宽度审计 (校准字宽模型, 纯离线)。

口径 (docs/REPORT_wrap_and_title.md §1.2, 已在 GR_ZH98/111 的 EE RAM 里复核):
    汉字/全角标点 16 + tracking 1 = 17
    ASCII 0x21..0x7E 8 + 1        = 9
    空格 0x20        3 + 1        = 4
    可行容量: 一行 = 15 个全角字 (255) < wrapW 270 ≤ 272

输入: 版本目录 (读 <VER>_text_long.csv 的 text_edited 列)
输出: 每行的宽度、超宽行清单 (关掉自动折行后它们会溢出到框外)

用法: python r69_lineaudit.py <版本目录> [--cap 270] [--top 30]
"""
import argparse
import csv
import io
import os
import re
import sys

WIDE = 16          # 汉字 / 全角标点
ASCII = 8
SPACE = 3
TRACK = 1


def char_w(ch):
    o = ord(ch)
    if ch == ' ':
        return SPACE
    if 0x21 <= o <= 0x7E:
        return ASCII
    return WIDE


def line_w(s):
    return sum(char_w(c) + TRACK for c in s.strip())


def segments(text):
    """把 text_edited 展开成"引擎真正会看到的段" —— {Warp}/{WRAP} 与空行都是段界。"""
    t = re.sub(r'\{(?:Warp|WRAP|warp|wrap)\}', '\x01', text)
    out = []
    for para in t.split('\n'):
        if para == '':
            out.append(('BLANK', ''))          # 空行 ⇒ {p}
            continue
        for seg in para.split('\x01'):
            out.append(('SEG', seg))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('verdir')
    ap.add_argument('--cap', type=int, default=270)
    ap.add_argument('--top', type=int, default=30)
    a = ap.parse_args()
    verdir = os.path.abspath(a.verdir)
    ver = os.path.basename(verdir)
    csvp = os.path.join(verdir, 'text', '%s_text_long.csv' % ver)
    assert os.path.isfile(csvp), csvp
    rows = list(csv.reader(io.open(csvp, encoding='utf-8-sig', newline='')))
    hdr = rows[0]
    i_edit = hdr.index('text_edited')
    i_id = hdr.index('id')

    n_item = n_seg = 0
    over = []
    widths = []
    for r in rows[1:]:
        if len(r) <= i_edit:
            continue
        n_item += 1
        for kind, seg in segments(r[i_edit]):
            if kind == 'BLANK':
                continue
            n_seg += 1
            w = line_w(seg)
            widths.append(w)
            if w > a.cap:
                over.append((w, r[i_id], seg.strip()))
    widths.sort()
    print('===== %s : 特别收录 (SFXML) 逐行宽度审计 =====' % ver)
    print('  条目 %d ; 段 (引擎折行单位) %d ; 容量 = %d' % (n_item, n_seg, a.cap))
    if widths:
        print('  段宽: 最大 %d / 中位 %d / 最小 %d' %
              (widths[-1], widths[len(widths) // 2], widths[0]))
        print('  > %d 的段 (关掉自动折行后会溢出): %d 个 (%.1f%%)'
              % (a.cap, len(over), 100.0 * len(over) / n_seg))
        print('  其中 > %d (16 全角字) 的: %d 个' % (272, sum(1 for w in widths if w > 272)))
    over.sort(reverse=True)
    print('\n  最宽的前 %d 段:' % a.top)
    for w, i, s in over[:a.top]:
        print('    %4d  (=%4.1f 全角字)  %-16s  %s%s'
              % (w, w / 17.0, i, s[:34], '…' if len(s) > 34 else ''))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
