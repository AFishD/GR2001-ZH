# -*- coding: utf-8 -*-
"""r39 探针: 全盘容器普查 —— 只读, 不写任何盘/字符集。"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
print('# REPO = %s' % REPO)
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
print('容器总数 = %d' % len(conts))
print('按 kind: %s' % dict(collections.Counter(c['kind'] for c in conts)))
print('按 img : %s' % dict(collections.Counter(c['img'] for c in conts)))
print('按扩展名: %s' % dict(collections.Counter(
    os.path.splitext(c['name'].upper())[1] for c in conts).most_common(30)))

# 每个 kind 的前几个名字
bykind = collections.defaultdict(list)
for c in conts:
    bykind[c['kind']].append(c)
for k in sorted(bykind):
    names = [c['name'] for c in bykind[k]]
    print('\n== %s (%d) ==' % (k, len(names)))
    print('   例: %s' % ' | '.join(names[:8]))

# 解压 blob 统计
print('\n--- 解压 blob 大小 ---')
tot = 0
for c in conts:
    b, raw = FU.container_blob(iso, c)
    c['_blob'] = b
    tot += len(b)
print('解压合计 %.1f MB (报告说 1583.7 MB)' % (tot / 1048576.0))

# 每个 kind 的"可打印串"个数 (>=8) 与是否有非 ASCII
print('\n--- 每 kind: blob 字节 / 可读串(>=8, 引擎字母表) / 纯 ASCII 串 / 含高位字节串 ---')
rows = []
for k in sorted(bykind):
    nb = nrun = n_hi = n_ascii = 0
    for c in bykind[k]:
        b = c['_blob']
        nb += len(b)
        for m in idx.run_re(8).finditer(b):
            s = m.group(0)
            nrun += 1
            if max(s) < 0x80:
                n_ascii += 1
            else:
                n_hi += 1
    rows.append((k, len(bykind[k]), nb, nrun, n_ascii, n_hi))
print('%-10s %6s %12s %9s %9s %9s' % ('kind', 'n', 'blobB', 'run>=8', 'ascii', 'high'))
for r in rows:
    print('%-10s %6d %12d %9d %9d %9d' % r)

# 中文命中: 每个 kind 里解码出的 CJK 字符集合
print('\n--- 每 kind 解出的 CJK 字符 (>=8 的可读串里) ---')
CJK = re.compile(r'[\u4e00-\u9fff]')
for k in sorted(bykind):
    s = set()
    for c in bykind[k]:
        for m in idx.run_re(8).finditer(c['_blob']):
            s |= set(CJK.findall(idx.decode_text(m.group(0))))
    if s:
        print('%-10s %4d 个中文: %s' % (k, len(s), ''.join(sorted(s))[:60]))

iso.close()
