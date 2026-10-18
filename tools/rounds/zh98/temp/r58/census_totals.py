# -*- coding: utf-8 -*-
r"""r58: 普查的量化小结 (登记 vs 未登记; 只读 census_r58.json)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import font_compact as FC                                              # noqa: E402

d = json.load(io.open(os.path.join(HERE, 'census_r58.json'), encoding='utf-8'))
un = [r for r in d['rows'] if not FC.registry_match(r['name'])]
reg = [r for r in d['rows'] if FC.registry_match(r['name'])]


def agg(rows):
    return (len(rows),
            sum(r['gen']['G2']['runs'] for r in rows),
            sum(r['gen']['G2']['pair_runs'] for r in rows),
            sum(r['gen']['G0']['delta_runs_bytes'] for r in rows),
            sum(r['gen']['G1']['delta_runs_bytes'] for r in rows))


for nm, rows in (('登记容器', reg), ('未登记容器', un)):
    n, runs, pruns, d0, d1 = agg(rows)
    print('%-8s 容器 %5d | >=2 汉字段 %9d | 含对偶码的段 %9d | 段口径改字节 G0->G2 %8d / G1->G2 %8d'
          % (nm, n, runs, pruns, d0, d1))
    print('         每"含对偶码段"平均改动 %.4f 字节' % (d1 / max(1, pruns)))
print('未登记里 delta_runs_bytes == 0 的容器: %d 个'
      % sum(1 for r in un if r['gen']['G1']['delta_runs_bytes'] == 0))
print('未登记里"汉字数 >= 1000 且 delta <= 32 字节"的容器 (巨型媒体里的单字节码噪声): %d 个'
      % sum(1 for r in un if r['gen']['G2']['n_cjk'] >= 1000
            and r['gen']['G1']['delta_runs_bytes'] <= 32))
print('未登记里"最长串 >= 6 且 delta <= 4 字节"的容器: %d 个'
      % sum(1 for r in un if max(g['max_run'] for g in r['gen'].values()) >= 6
            and r['gen']['G1']['delta_runs_bytes'] <= 4))
