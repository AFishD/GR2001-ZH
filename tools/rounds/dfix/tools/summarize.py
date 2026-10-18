# -*- coding: utf-8 -*-
r"""summarize.py —— 把 4 张候选盘的 meta.json 汇总成一张 Markdown 站点表（证据文件）。
用法: python work\builds\GR_DFIX\tools\summarize.py
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TAGS = ['DFIX_pkt', 'DFIX_icon', 'DFIX_fp', 'DFIX_pkt_fp']

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
out = []
P = lambda s='': (print(s), out.append(s))  # noqa: E731


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


P('# DFIX 候选修复盘 —— 站点与产物汇总（自动生成，勿手改）')
P()
P('生成器: `work\\builds\\GR_DFIX\\tools\\summarize.py`')
P()
base = os.path.join(ROOT, 'base', 'GR_REBUILD2400_base.iso')
P('## 基底')
P()
P('| 项 | 值 |')
P('|---|---|')
P('| 文件 | `work\\builds\\GR_DFIX\\base\\GR_REBUILD2400_base.iso` |')
P('| sha256 | `%s` |' % sha(base))
P('| 尺寸 | %d B |' % os.path.getsize(base))
P()
for t in TAGS:
    mp = os.path.join(ROOT, t + '.meta.json')
    if not os.path.exists(mp):
        P('- ⚠ 缺 %s' % mp)
        continue
    m = json.load(open(mp, encoding='utf-8'))
    iso = os.path.join(ROOT, m['out_file'])
    P('## %s' % t)
    P()
    P('| 项 | 值 |')
    P('|---|---|')
    P('| 修复集 | `%s` |' % m['sets_expr'])
    P('| 站点数 | %d |' % m['site_count'])
    P('| 产物 | `work\\builds\\GR_DFIX\\%s` |' % m['out_file'])
    P('| sha256（**实算复核**） | `%s` |' % sha(iso))
    P('| sha256（meta 记录） | `%s` |' % m['sha256'])
    P('| 尺寸 | %d B |' % m['bytes'])
    P('| diff_runs | %d 段 / %d 字节 |' % (m['diff_run_count'], m['diff_bytes']))
    P('| 自证 | ' + ', '.join('%s=%s' % (k, 'OK' if v else 'FAIL') for k, v in m['selfcheck'].items()) + ' |')
    P()
    P('| VA | ISO 偏移 | 原字 | 新字 | 组 | 站点 |')
    P('|---|---|---|---|---|---|')
    for s in m['sites']:
        P('| `%s` | `%s` | `%s` | `%s` | %s | %s |' % (s['va'], s['iso_off_hex'], s['orig'], s['new'],
                                                         s['group'], s['name']))
    P()
    P('diff_runs: ' + ' ; '.join('`%s`+%d: %s→%s' % (r['iso_off'], r['len'], r['old'], r['new'])
                                 for r in m['diff_runs']))
    P()

dst = os.path.join(ROOT, 'audit', 'summary_sites.md')
with open(dst, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(out) + '\n')
print('\n写出: %s' % dst)
