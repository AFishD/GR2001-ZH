# -*- coding: utf-8 -*-
"""r39: 核对生效的判据 (MSG_RE / 取到的阈值) 与旧基线 container_debug.json 的差异。只读。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_containers as DC

print('MSG_RE      = %r' % DC.MSG_RE.pattern)
print('WORD_SPACE  = %d' % DC.WORD_MIN_SPACE_WORD)
print('WORDISH     = len>=%d alnum>=%.2f' % (DC.WORDISH_MIN_LEN, DC.WORDISH_ALNUM_RATIO))
print('MIN_*       = distinct %d score %.1f text_ratio %.2f'
      % (DC.MIN_DISTINCT, DC.MIN_TEXT_SCORE, DC.MIN_TEXT_RATIO))
for s in ("'Aufkl装rung'", 'AB44##333DC(', 'model=res door02', 'leafy_tree_foliage.bmp',
          'shermanlevel1', 'D01 Beach', 'B2}rB巨何pBV用pBk'):
    print('   %-30r → %r' % (s, DC.MSG_RE.search(s) is not None))

t = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
print('debug 记录 %d 条 (4709 说明是旧门 b2 那次的文件?)' % len(t))
keys = sorted(t[0].keys())
print('debug 字段: %s' % keys)
risky = [x for x in t if x['risk']]
print('risky=%d' % len(risky))
# 用**新代码**的字段名重新套闸门
if 'text_ratio' in t[0]:
    for (d, s, m) in ((10, 10, .15), (10, 10, .20), (10, 10, .25), (10, 10, .30)):
        keep = [x for x in risky if x['distinct'] >= d and x['score'] >= s and x['text_ratio'] >= m]
        print('   新门 d>=%d s>=%d tr>=%.2f ⇒ 容器 %4d 串 %7d' %
              (d, s, m, len(keep), sum(x['distinct'] for x in keep)))
else:
    print('!! debug 文件是旧字段')
