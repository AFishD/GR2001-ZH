# -*- coding: utf-8 -*-
"""用 view 表自带的 has_cjk / cjk_run 列统计 (只读)。"""
import csv
import io
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TD = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text')
tot_has = 0
per_kind = {}
examples = []
for fn in sorted(os.listdir(TD)):
    if '_view_' not in fn or not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(TD, fn), encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        n = has = 0
        for r in rd:
            n += 1
            h = (r.get('has_cjk') or '').strip().lower()
            if h in ('1', 'true', 'yes', 'y'):
                has += 1
                k = (r.get('source_kind') or '?')
                per_kind[k] = per_kind.get(k, 0) + 1
                try:
                    run = int(r.get('cjk_run') or 0)
                except ValueError:
                    run = 0
                if run >= 4 and len(examples) < 400:
                    examples.append((fn, k, r.get('container'), r.get('offset'),
                                     r.get('len_bytes'), run, (r.get('text') or '')[:60]))
        tot_has += has
        print('%-42s 行 %6d  has_cjk %5d' % (fn, n, has))
print('合计 has_cjk = %d' % tot_has)
print('按 source_kind:', dict(sorted(per_kind.items(), key=lambda kv: -kv[1])))
print('--- 例子 (cjk_run>=4, 前 60 条) ---')
for e in examples[:60]:
    print('  %-34s off=%-10s len=%-6s run=%-3s %r' % ((e[2] or '')[:34], e[3], e[4], e[5], e[6]))
print('... 共 %d 条 cjk_run>=4' % len(examples))
