# -*- coding: utf-8 -*-
r"""count_tri.py — 数「△」(0xB1) 在用户丰富版译文里出现多少次

背景: 字面 △ 在 text 里 0 处 ⇒ 它由 tcslib 的**标记系统**（charset JSON 的 markers/mark_codes）
      在注入时才展开。决策需要这个数字（选 (a) 改对偶码 还是 (b) 改 ELF 保 20px）。
"""
import glob
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cj = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
d = json.load(open(cj, encoding='utf-8'))
for k in ('markers', 'mark_codes', 'protected'):
    v = d.get(k)
    print('%s = %s' % (k, json.dumps(v, ensure_ascii=False)[:400]))
print()

markers = d.get('markers') or []
mark_codes = d.get('mark_codes') or {}
print('标记个数 %d ; mark_codes 键 %s' % (len(markers) if hasattr(markers, '__len__') else -1, list(mark_codes)[:20] if isinstance(mark_codes, dict) else mark_codes))
print()

# 找出哪个标记对应 0xB1 / △
tri_mark = None
if isinstance(mark_codes, dict):
    for k, v in mark_codes.items():
        s = json.dumps(v, ensure_ascii=False)
        if '177' in s or '0xB1' in s.upper() or 'B1' in s.upper() or '561A' in s.upper() or '△' in s:
            print('  ★ 候选: %s -> %s' % (k, s[:200]))
            tri_mark = k
print('  ⇒ 推断标记: %s' % tri_mark)
print()

# 在文本里统计各标记出现次数
dirs = ['work/builds/GR_ZH109/text_backup_before_reduce', 'work/builds/GR_ZH113b/text']
for dd in dirs:
    p = os.path.join(REPO, dd)
    if not os.path.exists(p):
        print('(缺 %s)' % dd)
        continue
    files = glob.glob(os.path.join(p, '*.csv'))
    total = {}
    rows = 0
    for f in files:
        try:
            txt = open(f, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        rows += 1
        for m in (markers if isinstance(markers, (list, tuple)) else []):
            if not isinstance(m, str) or not m:
                continue
            c = txt.count(m)
            if c:
                total[m] = total.get(m, 0) + c
    print('%s : 文件 %d' % (dd, rows))
    if total:
        for m, c in sorted(total.items(), key=lambda kv: -kv[1])[:15]:
            print('    %-12r %d 次' % (m, c))
    else:
        print('    未找到列表型标记')
    print()
