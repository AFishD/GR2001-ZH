# -*- coding: utf-8 -*-
r"""splice45.py — 把 sec45_new.md 的内容替换进 REPORT_record_band_fix.md 的 §4.5
（只替换从 "### 4.5 实机 A/B" 到下一个 "## 5. 已知限制" 之间的内容，其余一字不动）。

用法: python splice45.py <report.md> <sec45_new.md> [--dry]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    rep, sec = sys.argv[1], sys.argv[2]
    dry = '--dry' in sys.argv
    lines = io.open(rep, encoding='utf-8').read().splitlines(True)
    new = io.open(sec, encoding='utf-8').read()
    i0 = next((i for i, ln in enumerate(lines) if ln.startswith('### 4.5 ')), None)
    i1 = next((i for i, ln in enumerate(lines) if ln.startswith('## 5. ')), None)
    assert i0 is not None and i1 is not None and i0 < i1, (i0, i1)
    print('替换 %s 第 %d..%d 行 (共 %d 行) → 新内容 %d 行'
          % (os.path.basename(rep), i0 + 1, i1, i1 - i0, new.count('\n')))
    out = ''.join(lines[:i0]) + new + ('' if new.endswith('\n\n') else '\n') + ''.join(lines[i1:])
    if dry:
        print('(dry-run, 未写入)')
        return
    io.open(rep, 'w', encoding='utf-8', newline='\n').write(out)
    print('已写入 %s (新大小 %d)' % (rep, len(out.encode('utf-8'))))


if __name__ == '__main__':
    main()
