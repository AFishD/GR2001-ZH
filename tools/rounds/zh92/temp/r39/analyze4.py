# -*- coding: utf-8 -*-
"""r39: 最终确定第 3 关 = distinct + score + clean_ratio (单判据)。检查各阈值丢什么。只读。"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
risky = [x for x in D if x['risk']]
safe = [x for x in D if not x['risk']]

for thr in (0.0005, 0.001, 0.0015, 0.002, 0.003, 0.005, 0.01):
    k = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['clean_ratio'] >= thr]
    cj = sum(x['cjk2'] for x in k)
    print('clean_ratio>=%-7.4f ⇒ 容器 %4d 串 %7d  cjk2 %5d  按 kind %s'
          % (thr, len(k), sum(x['distinct'] for x in k), cj,
             dict(collections.Counter(x['kind'] for x in k))))

base = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10]
print('\n(distinct/score 已过、仅看 clean_ratio 的 %d 个容器)' % len(base))
v = sorted(x['clean_ratio'] for x in base)
q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
print('   clean_ratio p10=%.6f p25=%.6f p50=%.6f p75=%.6f p90=%.6f'
      % (q(.1), q(.25), q(.5), q(.75), q(.9)))

print('\n--- clean_ratio>=0.002 放行的容器按 kind 的串数 ---')
k = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['clean_ratio'] >= 0.002]
agg = collections.Counter()
for x in k:
    agg[x['kind']] += x['distinct']
print('   %s' % dict(agg))
print('   达 2000 上限的容器 %d' % sum(1 for x in k if x['capped']))
print('\n--- 放行里串数 top 20 ---')
for x in sorted(k, key=lambda y: -y['distinct'])[:20]:
    print('   %-8s d=%6d clean=%.5f tr=%.3f cjk2=%4d %-36s %10d B' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['text_ratio'], x['cjk2'],
           x['name'][:36], x['blob']))
print('\n--- clean_ratio>=0.002 但 text_ratio<0.15 的容器 (文本但不像句子: 名字表) ---')
k2 = [x for x in k if x['text_ratio'] < 0.15]
print('   %d 个, 串 %d; 例:' % (len(k2), sum(x['distinct'] for x in k2)))
for x in sorted(k2, key=lambda y: -y['distinct'])[:15]:
    print('   %-8s d=%6d clean=%.5f tr=%.3f %-38s' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['text_ratio'], x['name'][:38]))
print('\n--- 被 clean_ratio<0.002 拒掉、但串数最多的 12 个 (确认都是压缩数据) ---')
lost = [x for x in base if x['clean_ratio'] < 0.002]
for x in sorted(lost, key=lambda y: -y['distinct'])[:12]:
    print('   %-8s d=%6d clean=%.7f tr=%.3f cjk2=%4d %-34s %10d B' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['text_ratio'], x['cjk2'],
           x['name'][:34], x['blob']))
print('   合计拒掉 %d 容器 %d 串' % (len(lost), sum(x['distinct'] for x in lost)))

print('\n--- 参考: 非风险类 (不过闸门) 的 clean_ratio ---')
for kk in ('MIS', 'ATR', 'XML', 'RES', 'TXT', 'ELF', 'ISO_FILE'):
    rs = [x for x in safe if x['kind'] == kk]
    if not rs:
        continue
    vv = sorted(x['clean_ratio'] for x in rs)
    print('   %-9s n=%4d 中位 %.6f  最小 %.7f' % (kk, len(vv), vv[len(vv) // 2], vv[0]))
