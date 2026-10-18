# -*- coding: utf-8 -*-
r"""r71p_check_final.py — ★ 逐条自查 (验收门禁 ★)

对**最终三张表**逐字检查 (口径 = tools/font_pipeline/data/charset_compiled_zh16.json 的
pair_of + codes; ASCII 一律放行):
  · 每条文本的缺字数 (种 / 次) —— 逐条打印
  · 16 条低精准度 + 9 条高精准度逐条标注
  · {WRAP} 写法/位置自查 (复用 tcslib 的权威口径)
  · 表级 sha256 (便于与历史比对)

用法: python r71p_check_final.py <text 目录> [--label 名称]
"""
import argparse
import csv
import glob
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
LOW = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]
HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044',
      'SFXML:T0046', 'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']
WRAP = T.WRAP_RE                    # ★ 权威口径 (两种拼写 + 大小写不敏感)

d = json.load(io.open(CS, encoding='utf-8'))
HAVE = set(d['pair_of']) | set(d['codes']) | set(chr(i) for i in range(0x20, 0x7F))


def miss(t):
    return [ch for ch in WRAP.sub('', t or '') if ord(ch) >= 0x80 and ch not in HAVE]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('textdir')
    ap.add_argument('--label', default='')
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.textdir, '*_text_*.csv')))
    files = [f for f in files if not f.endswith('_locked.csv')]
    print('===== 逐条自查: %s =====' % (a.label or a.textdir))
    print('字库: %s (%d 字: pair %d + single %d)'
          % (os.path.basename(CS), len(d['pair_of']) + len(d['codes']),
             len(d['pair_of']), len(d['codes'])))
    print('表: %d 张' % len(files))
    tot_k, tot_n, bad_wrap = 0, 0, 0
    worst = []
    for f in files:
        rows = list(csv.DictReader(io.open(f, encoding='utf-8-sig', newline='')))
        name = os.path.basename(f)
        tk, tn = set(), 0
        print('\n-- %s (%d 行) --' % (name, len(rows)))
        for r in rows:
            t = r.get('text_edited') or ''
            m = miss(t)
            tk |= set(m)
            tn += len(m)
            probs = T.scan_wrap_placement(t)
            if probs:
                bad_wrap += len(probs)
                print('   [WRAP位置问题] %s : %s' % (r['id'], probs[:2]))
            if m or r['id'] in LOW or r['id'] in HI:
                tag = ''
                if r['id'] in LOW:
                    tag = '  << 低精准度'
                elif r['id'] in HI:
                    tag = '  << 高精准度'
                print('   %-14s 缺 %2d 种 / %2d 次 %s%s'
                      % (r['id'], len(set(m)), len(m),
                         (''.join(sorted(set(m))) if m else 'OK'), tag))
            elif m:
                worst.append((r['id'], ''.join(sorted(set(m) ))))
        print('   小计: 缺 %d 种 / %d 次' % (len(tk), tn))
        tot_k += len(tk)
        tot_n += tn
        print('   sha256 = %s' % T.sha256_file(f))
    print('\n===== 合计 =====')
    print('  三张表合计缺字: %d 种 / %d 次   %s'
          % (tot_k, tot_n, '✓' if tot_k == 0 else '✗'))
    print('  {WRAP} 位置问题: %d  %s' % (bad_wrap, '✓' if bad_wrap == 0 else '✗'))
    if worst:
        print('  其它条目缺字: %s' % worst)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
