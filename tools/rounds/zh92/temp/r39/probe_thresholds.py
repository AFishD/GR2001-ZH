# -*- coding: utf-8 -*-
"""r39 探针 2: 文本判定阈值的可信度 —— 覆盖率/字率/中文分布。只读。"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ISO)
cs = T.Charset()
idx = FU.CharsetIndex()
conts = FU.build_container_list(iso)

CJK = re.compile(r'[\u4e00-\u9fff]')
VIS = re.compile(r'[0-9A-Za-z \.\-_/\\:;,\'\"!?()\[\]<>+=*&%$#@~`^{}|]')

bykind = collections.defaultdict(list)
for c in conts:
    bykind[c['kind']].append(c)

print('%-10s %6s %10s %10s %10s %10s %10s' %
      ('kind', 'n', 'blobMB', 'cov%', 'cjk_chars', 'vis>=.85', 'word>=.5'))
tot_hi = collections.defaultdict(set)
for k in sorted(bykind):
    nb = cov = 0
    cjkset = set()
    n_vis = n_word = n_run8 = 0
    for c in bykind[k]:
        b, _raw = FU.container_blob(iso, c)
        nb += len(b)
        covered = 0
        for m in idx.run_re(8).finditer(b):
            s = m.group(0)
            covered += len(s)
            n_run8 += 1
            t = cs.decode(s)[0]
            cjkset |= set(CJK.findall(t))
            vis = sum(1 for ch in t if VIS.match(ch)) / max(1, len(t))
            if vis >= 0.85:
                n_vis += 1
            if vis >= 0.85 and ' ' in t and len(t) >= 12:
                n_word += 1
        cov += covered
    tot_hi[k] = cjkset
    print('%-10s %6d %10.1f %9.2f%% %10d %10d %10d' %
          (k, len(bykind[k]), nb / 1048576.0, 100.0 * cov / max(1, nb),
           len(cjkset), n_vis, n_word))

print('\n--- 各 kind 解出的中文 (>=8 可读串) ---')
for k in sorted(tot_hi):
    s = tot_hi[k]
    if s:
        print('%-10s %4d: %s' % (k, len(s), ''.join(sorted(s))[:70]))

# 纯 ASCII 高覆盖容器的例子
print('\n--- 覆盖率最高的 12 个容器 (>=8 可读串占 blob 比) ---')
sc = []
for c in conts:
    b, _raw = FU.container_blob(iso, c)
    if len(b) < 512:
        continue
    cov = sum(m.end() - m.start() for m in idx.run_re(8).finditer(b))
    sc.append((cov / len(b), c['kind'], c['name'], len(b)))
sc.sort(reverse=True)
for r in sc[:12]:
    print('  %.3f  %-9s %-40s %8d B' % r)

iso.close()
