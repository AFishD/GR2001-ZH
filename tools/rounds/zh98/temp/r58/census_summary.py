# -*- coding: utf-8 -*-
r"""r58 普查分析: 把 census_r58.json 收敛成"**真文本**候选"(而不是二进制巧合) 的那几张表。

判读口径 (与工具同源):
  · 登记容器 (名字匹配 CONTAINER_TEXT_REGISTRY) ⇒ 本轮的覆盖面说明;
  · "长汉字串" = 任一代下 max_run >= 6 ⇒ 才可能是引擎会显示的文本 (工具的 texty 判据下限);
  · 其余 (max_run 2~5 且夹在二进制里) ⇒ 二进制巧合, 只计数 + 举例。
再与**普查表** (GR_ZH107/text/*_view_*.csv 里 any-CJK 的容器) 对表。
"""
import collections
import csv
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import font_compact as FC                                              # noqa: E402

doc = json.load(io.open(os.path.join(HERE, 'census_r58.json'), encoding='utf-8'))
rows = doc['rows']
print('普查: 扫 %d 容器 (跳过无"换代会变对偶码" %d; 展开态 >4MB 跳过 %d); '
      '段口径会变的容器 %d; 耗时 %.0fs'
      % (doc['containers_scanned'], doc['containers_skipped_no_changed_pair'],
         doc['containers_skipped_oversize'], len(rows), doc['seconds']))

reg, longrun, short, other = [], [], [], []
for r in rows:
    rent = FC.registry_match(r['name'])
    mr = max(g['max_run'] for g in r['gen'].values())
    if rent:
        reg.append((r, rent))
    elif mr >= 6:
        longrun.append(r)
    elif mr >= 2:
        short.append(r)
    else:
        other.append(r)
print('\n① 登记容器 (名字匹配登记表) 有段口径改动的: %d 个' % len(reg))
for (r, rent) in reg:
    print('   %-38s max_run=%d 段 %s  改 %d B (G1→G2)  %r'
          % (r['container'], max(g['max_run'] for g in r['gen'].values()),
             [r['gen'][g]['pair_runs'] for g in ('G0', 'G1', 'G2')],
             r['gen']['G1']['delta_runs_bytes'], r['gen']['G2']['cjk_text'][:40]))

print('\n② ★ 未登记但"最长汉字串 >= 6"的容器 (工具的 texty 判据下限): %d 个' % len(longrun))
longrun.sort(key=lambda r: -max(g['max_run'] for g in r['gen'].values()))
for r in longrun:
    print('   %-38s max_run=%-3d 汉字 %-6d 段 %-5d 改 %d B  txt=%r'
          % (r['container'], max(g['max_run'] for g in r['gen'].values()),
             r['gen']['G2']['n_cjk'], r['gen']['G2']['runs'],
             r['gen']['G1']['delta_runs_bytes'], r['gen']['G2']['cjk_text'][:50]))

print('\n③ 未登记、最长串 2..5 的容器 (二进制巧合): %d 个' % len(short))
ext = collections.Counter(os.path.splitext(r['name'])[1].upper() for r in short)
print('   按扩展名: %s' % ', '.join('%s×%d' % kv for kv in ext.most_common(12)))
big = sorted(short, key=lambda r: -r['gen']['G1']['delta_runs_bytes'])[:10]
for r in big:
    print('   %-38s max_run=%d 改 %d B  txt=%r'
          % (r['container'], max(g['max_run'] for g in r['gen'].values()),
             r['gen']['G1']['delta_runs_bytes'], r['gen']['G2']['cjk_text'][:40]))

print('\n④ 与**普查表**对表 (GR_ZH107/text/*_view_*.csv 里 any-CJK 的容器)')
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'text')
cjk = collections.defaultdict(lambda: dict(rows=0, any=0, has=0, maxrun=0))
for fn in sorted(os.listdir(TDIR)):
    if not (fn.endswith('.csv') and '_view_' in fn):
        continue
    for rr in csv.DictReader(io.open(os.path.join(TDIR, fn), encoding='utf-8', newline='')):
        c = (rr.get('container') or '').strip().lstrip('\ufeff')
        if not c:
            continue
        d = cjk[c]
        d['rows'] += 1
        try:
            run = int(rr.get('cjk_run') or 0)
        except ValueError:
            run = 0
        d['maxrun'] = max(d['maxrun'], run)
        d['any'] += (run >= 1)
        d['has'] += ((rr.get('has_cjk') or '').strip() == 'yes')
anyc = {c: d for c, d in cjk.items() if d['any']}
print('   普查表里"含 ≥1 个汉字"的容器 %d 个 (其中 has_cjk 即 ≥2 连续: %d 个)'
      % (len(anyc), sum(1 for d in anyc.values() if d['has'])))
miss = []
for c, d in sorted(anyc.items(), key=lambda kv: -kv[1]['maxrun']):
    name = c.split(' ', 1)[1] if ' ' in c else c
    if FC.registry_match(name):
        continue
    miss.append((c, d))
print('   其中**没被登记表覆盖**的: %d 个; 按"普查表最长串"分布: %s'
      % (len(miss), ', '.join('%d字×%d' % kv for kv in
                              sorted(collections.Counter(d['maxrun'] for _c, d in miss).items()))))
print('   （这些是不是真文本, 见 ② / ③ 的判读; 普查表的"汉字"绝大多数是重音字节撞上单字节码）')
for (c, d) in miss[:25]:
    if d['maxrun'] >= 2:
        print('      %-44s 行 %-5d anyCJK %-5d 最长 %d' % (c, d['rows'], d['any'], d['maxrun']))
json.dump(dict(registered=[r['container'] for r, _e in reg],
               long_run_unregistered=[r['container'] for r in longrun],
               short_run_unregistered=len(short),
               view_any_cjk=len(anyc), view_unregistered=len(miss),
               view_unregistered_list=[c for c, _d in miss]),
          io.open(os.path.join(HERE, 'census_summary.json'), 'w', encoding='utf-8',
                  newline='\n'), ensure_ascii=False, indent=1)
