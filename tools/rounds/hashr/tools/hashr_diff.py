# -*- coding: utf-8 -*-
r"""hashr_diff.py — 产物盘 vs 基底盘的**逐字节差异清单** (区间级)

    python work/builds/GR_HASHR/tools/hashr_diff.py [--base <iso>] [--prod <iso>] [--tag X]

输出:
  work/builds/GR_HASHR/audit/diff_spans.json   全部差异区间 [{off, len, base_hex, prod_hex}]
  work/builds/GR_HASHR/audit/diff_spans.txt    人读版 (区间 + 前 200 段的字节)
"""
import argparse
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(REPO, 'work', 'builds', 'GR_HASHR')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2',
                                                   'GR_FA2400_K2.iso'))
    ap.add_argument('--prod', default=os.path.join(OUT, 'GR_HASHR2400.iso'))
    ap.add_argument('--tag', default='GR_HASHR2400')
    a = ap.parse_args()
    sa, sb = os.path.getsize(a.base), os.path.getsize(a.prod)
    assert sa == sb, (sa, sb)
    spans = []
    with open(a.base, 'rb') as fa, open(a.prod, 'rb') as fb:
        pos = 0
        while pos < sa:
            n = min(1 << 22, sa - pos)
            x, y = fa.read(n), fb.read(n)
            if x != y:
                i = 0
                while i < n:
                    if x[i] != y[i]:
                        j = i
                        while j < n and x[j] != y[j]:
                            j += 1
                        spans.append((pos + i, j - i, x[i:j], y[i:j]))
                        i = j
                    else:
                        i += 1
            pos += n
    tot = sum(s[1] for s in spans)
    lines = ['# %s vs %s' % (os.path.basename(a.prod), os.path.basename(a.base)),
             '# ISO %d B ; 差异区间 %d 段 ; 差异字节 %d' % (sa, len(spans), tot),
             '# sha256 base = %s' % hashlib.sha256(open(a.base, 'rb').read()).hexdigest()
             if sa < (1 << 31) else '',
             '# 格式: off hex | len | base_hex -> prod_hex (≤48 B 全列)',
             '']
    js = []
    for (off, ln, xb, yb) in spans:
        js.append(dict(off=off, off_hex='0x%X' % off, len=ln,
                       base=xb.hex(), prod=yb.hex()))
        lines.append('0x%08X | %5d | %s%s -> %s%s'
                     % (off, ln, xb[:48].hex(), '…' if ln > 48 else '',
                        yb[:48].hex(), '…' if ln > 48 else ''))
    with io.open(os.path.join(OUT, 'audit', 'diff_spans.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(base=a.base, prod=a.prod, iso_size=sa, n_spans=len(spans),
                       n_bytes=tot, spans=js), f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, 'audit', 'diff_spans.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('差异区间 %d 段 / %d B → audit/diff_spans.{json,txt}' % (len(spans), tot))
    print('前 6 段:')
    for (off, ln, xb, yb) in spans[:6]:
        print('  0x%08X %4dB  %s -> %s' % (off, ln, xb[:16].hex(), yb[:16].hex()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
