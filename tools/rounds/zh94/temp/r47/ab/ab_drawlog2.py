# -*- coding: utf-8 -*-
r"""ab_drawlog2.py — 从 drawlog 里抽出**某一帧画出的中文文本** (只留 CJK 连续串)。

用法: python ab_drawlog2.py <drawlog> <f1,f2,...> [--min 2]
用途: 一眼看出"这一帧是什么页面"——例如目标长文页会打印出
      「在 Tom Clancy 的幽灵行动中」「你是一名美军顶级步兵部队的一员」等。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

CS = tcslib.Charset()
CJK = re.compile(r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]{2,}')


def dec(b):
    out, i = [], 0
    while i < len(b):
        v = b[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif i + 1 < len(b) and (v, b[i + 1]) in CS.pair_of:
            out.append(CS.pair_of[(v, b[i + 1])]); i += 2
        elif v in CS.codes:
            out.append(CS.codes[v]); i += 1
        else:
            i += 1
    return ''.join(out)


def main():
    p = sys.argv[1]
    want = set(int(x) for x in sys.argv[2].split(','))
    minlen = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 2
    buf = {f: [] for f in want}
    with io.open(p, encoding='utf-8', errors='replace') as fh:
        for ln in fh:
            m = re.match(r'F(\d+) ', ln)
            if not m:
                continue
            fr = int(m.group(1))
            if fr not in want:
                continue
            if '|' not in ln:
                continue
            try:
                b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
            except Exception:                                      # noqa: BLE001
                continue
            t = dec(b)
            for run in CJK.findall(t):
                if len(run) >= minlen:
                    buf[fr].append(run)
    for fr in sorted(want):
        runs = []
        for r in buf[fr]:
            if r not in runs:
                runs.append(r)
        print('=' * 90)
        print('F%d  中文串 %d 条:' % (fr, len(runs)))
        for r in runs[:60]:
            print('   %s' % r)


if __name__ == '__main__':
    main()
