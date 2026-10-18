# -*- coding: utf-8 -*-
"""r39: 用 per-container 统计标定容器级闸门阈值。只读。"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))

risky = [x for x in D if x['risk']]
safe = [x for x in D if not x['risk']]
print('risky=%d safe=%d' % (len(risky), len(safe)))
print('\n--- 非风险类 kind (不过闸门) 的统计, 用来看"真文本"长什么样 ---')
by = collections.defaultdict(list)
for x in safe:
    by[x['kind']].append(x)
print('%-10s %5s %8s %9s %9s %9s %9s' %
      ('kind', 'n', 'd_med', 'score_med', 'msgR_med', 'd_p10', 'score_p10'))
for k in sorted(by):
    v = by[k]
    med = lambda f: sorted(f(x) for x in v)[len(v) // 2]
    p10 = lambda f: sorted(f(x) for x in v)[max(0, len(v) // 10)]
    print('%-10s %5d %8d %9.2f %9.3f %9d %9.2f' %
          (k, len(v), med(lambda x: x['distinct']), med(lambda x: x['score']),
           med(lambda x: x['msg_ratio']), p10(lambda x: x['distinct']),
           p10(lambda x: x['score'])))
print('   safe 里 cjk2>0 的容器: %d' % sum(1 for x in safe if x['cjk2']))

print('\n--- 风险类: 现闸门(10/10/0.10)放行的 423 个里, 有多少带"伪造连续汉字" ---')
gate = lambda x, d, s, m: x['distinct'] >= d and x['score'] >= s and x['msg_ratio'] >= m
for (d, s, m) in ((10, 10, .10), (20, 30, .20), (20, 50, .20), (30, 50, .30),
                  (20, 50, .30), (30, 100, .30), (20, 80, .25), (40, 50, .25)):
    keep = [x for x in risky if gate(x, d, s, m)]
    cj = [x for x in keep if x['cjk2']]
    print('   distinct>=%-3d score>=%-5s msgR>=%.2f ⇒ 容器 %4d, 串 %7d, 其中 cjk2>0 的容器 %4d'
          ' (占其串 %d)' % (d, s, m, len(keep), sum(x['distinct'] for x in keep), len(cj),
                            sum(x['distinct'] for x in cj)))

print('\n--- 现闸门放行、且 cjk2>0 的容器 (按串数) top 25 ---')
keep = [x for x in risky if gate(x, 10, 10, .10) and x['cjk2']]
for x in sorted(keep, key=lambda y: -y['distinct'])[:25]:
    print('   %-9s d=%6d score=%8.2f msgR=%.3f cjk2=%5d  %-38s %10d B' %
          (x['kind'], x['distinct'], x['score'], x['msg_ratio'], x['cjk2'],
           x['name'][:38], x['blob']))

print('\n--- 现闸门**不**放行、但有 cjk2>0 的容器 (被丢掉的伪造汉字) ---')
dropped = [x for x in risky if not gate(x, 10, 10, .10) and x['cjk2']]
print('   数量 %d, 合计 cjk2 串 %d' % (len(dropped), sum(x['cjk2'] for x in dropped)))
for x in sorted(dropped, key=lambda y: -y['cjk2'])[:12]:
    print('   %-9s d=%6d score=%8.2f msgR=%.3f cjk2=%5d  %-38s %10d B' %
          (x['kind'], x['distinct'], x['score'], x['msg_ratio'], x['cjk2'],
           x['name'][:38], x['blob']))

print('\n--- 提高闸门会丢掉的**真实文本**容器 (人工看名字判断) ---')
for (d, s, m) in ((20, 50, .20), (30, 100, .30), (40, 100, .30)):
    lost = [x for x in risky if gate(x, 10, 10, .10) and not gate(x, d, s, m)]
    print('\n  [%d/%.0f/%.2f] 丢掉 %d 个容器:' % (d, s, m, len(lost)))
    byk = collections.Counter(x['kind'] for x in lost)
    print('     按 kind: %s' % dict(byk))
    for x in sorted(lost, key=lambda y: -y['distinct'])[:14]:
        print('     %-9s d=%6d score=%8.2f msgR=%.3f  %-40s' %
              (x['kind'], x['distinct'], x['score'], x['msg_ratio'], x['name'][:40]))
