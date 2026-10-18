# -*- coding: utf-8 -*-
r"""_find_page.py — 找「何为幽灵？」那条长文, 并列出页面正文里出现的 20 个受影响字。

只读 work/builds/GR_ZH94/text/。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TXT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '..', '..', '..', 'text'))
CSV = os.path.join(TXT, 'GR_ZH94_text_long.csv')
AFFECTED = '训火动习面务准可会出换下如以到中定斗是任'


def main():
    print('=== 找含「何为幽灵」的条目 ===')
    with io.open(CSV, encoding='utf-8', errors='replace') as f:
        rows = f.readlines()
    for i, ln in enumerate(rows):
        if '何为幽灵' in ln:
            print('--- 行 %d ---' % (i + 1))
            print(ln[:1500])
            print()
    print('=== 搜「战斗」(含 斗) 的条目首行 ===')
    n = 0
    for i, ln in enumerate(rows):
        if '战斗' in ln and 'SFXML:T' in ln:
            print('  行 %d: %s' % (i + 1, ln[:120].replace('\n', '')))
            n += 1
            if n > 8:
                break
    print('=== 按 id 列出含「斗」的条目 ===')
    ids = []
    for ln in rows:
        if 'SFXML:T' in ln and '斗' in ln:
            tid = ln.split(',')[3] if len(ln.split(',')) > 3 else '?'
            if tid not in ids:
                ids.append(tid)
    print('  %s' % ' '.join(ids[:40]))
    print('=== 含「抖」? ===')
    hit = [i + 1 for i, ln in enumerate(rows) if '抖' in ln]
    print('  行号: %s' % (hit[:10] if hit else '无 —— 文本表里没有「抖」字'))


if __name__ == '__main__':
    main()
