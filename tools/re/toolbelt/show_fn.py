# -*- coding: utf-8 -*-
r"""show_fn.py — 从 Ghidra 日志里抽出某个函数的 C 代码（按行号窗口, 简单可靠）

用法: python show_fn.py <日志> <函数名关键词> [<打印行数>]
"""
import io
import sys

log = sys.argv[1]
want = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def clean(l):
    i = l.find('.java> ')
    return l[i + 7:] if i >= 0 else l


lines = [clean(l) for l in io.open(log, encoding='utf-8', errors='replace').read().splitlines()]
start = None
for i, l in enumerate(lines):
    if want in l and l.strip().startswith('##'):
        start = i
        break
if start is None:
    print('✗ 没找到 %s' % want)
    sys.exit(1)
print('（从日志第 %d 行开始）' % (start + 1))
for l in lines[start:start + n]:
    if l.strip().startswith('## DONE') or (l.strip().startswith('##') and want not in l):
        break
    print(l)
