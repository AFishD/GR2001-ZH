# -*- coding: utf-8 -*-
r"""ab_summary.py — 把 ab_diff.json 归纳成"人看的"结论表 (ab_summary.md / .json)。

用法: python ab_summary.py <ab_diff.json> [--outdir <目录>] [--label ...]
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))

# 屏幕上那 5 组 y 行 → 是哪个字的哪一行 (由同帧放大图 + 盘上图集逐格对照确定)
ROW_MEANING = {
    134: '主菜单选中行「训练」的「训」最底一行',
    135: '同上 (2 行高的块)',
    161: '主菜单「战术演习」的「习」最底一行',
    162: '同上',
    216: '主菜单禁用行「快速任务」的「务」「任」最底一行',
    217: '同上',
    220: '引导屏「载入中…」的「中」最底一行',
    221: '同上',
    398: '主菜单底栏提示「学习游戏的基本操作。」的「习」最底一行',
    399: '同上',
}


def main():
    a = sys.argv[1:]
    src = a[0]
    outdir = a[a.index('--outdir') + 1] if '--outdir' in a else HERE
    d = json.load(io.open(src, encoding='utf-8'))
    det = [r for r in d['detail'] if 'n' in r]
    rowh = d['rowhist']
    L = []
    A = L.append
    A('# 实机 A/B 差异统计 (round48)')
    A('')
    A('* A (修前) = `%s`' % d['A'])
    A('* B (修后) = `%s`' % d['B'])
    A('* 同名帧 %d; **逐像素完全相同 %d 帧**; 有差异 %d 帧'
      % (d['frames_common'], d['frames_same'], d['frames_diff']))
    if det:
        A('* 每帧差异像素: 最少 %d / 最多 %d / 中位 %d'
          % (min(r['n'] for r in det), max(r['n'] for r in det),
             sorted(r['n'] for r in det)[len(det) // 2]))
        A('* 差异像素**只**落在这些屏幕行 (行 → 累计像素):')
        A('')
        A('| 屏幕 y 行 | 累计差异像素 | 是什么 |')
        A('|---|---|---|')
        for y in sorted(rowh, key=int):
            A('| %s | %d | %s |' % (y, rowh[y], ROW_MEANING.get(int(y), '(未归类)')))
        A('')
        A('* **其它所有屏幕像素 (底栏图标 / 金色选中框 / 背景 / 其它文字) 0 差异** —— '
          '因为差异像素集合就是上表这 %d 行。' % len(rowh))
        A('')
        A('## 逐帧明细 (前 40 帧有差异的)')
        A('')
        A('| 帧 | 差异像素 | 包围盒 x | 包围盒 y | 命中行 |')
        A('|---|---|---|---|---|')
        for r in det[:40]:
            A('| %s | %d | %d..%d | %d..%d | %s |'
              % (r['frame'], r['n'], r['x0'], r['x1'], r['y0'], r['y1'],
                 ','.join(str(v) for v in r['ys'])))
        A('')
        A('(共 %d 帧有差异)' % len(det))
    txt = '\n'.join(L) + '\n'
    p = os.path.join(outdir, 'ab_summary.md')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(txt)
    print(txt)
    print('→ %s' % p)
    summ = dict(frames_common=d['frames_common'], frames_same=d['frames_same'],
                frames_diff=d['frames_diff'], rowhist=rowh, row_meaning=ROW_MEANING,
                px_min=min(r['n'] for r in det) if det else 0,
                px_max=max(r['n'] for r in det) if det else 0)
    io.open(os.path.join(outdir, 'ab_summary.json'), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(summ, ensure_ascii=False, indent=1) + '\n')
    print('→ %s' % os.path.join(outdir, 'ab_summary.json'))


if __name__ == '__main__':
    main()
