# -*- coding: utf-8 -*-
r"""r71t_report.py — 读注入报告, 列出真正被重写的条目 + 容器用量"""
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH113_B', 'temp',
                                  'inject1_report.json'), encoding='utf-8'))
rows = d['rows']
ch = [r for r in rows if r.get('delta') or r.get('bytes_after') != r.get('bytes_before')]
print('报告 rows 总数 %d' % len(rows))
chg = [r for r in rows if r['bytes_after'] != r['bytes_before']
       or r.get('hard_breaks_after') != r.get('hard_breaks_before')]
print('字节数或硬断行数变化的行: %d' % len(chg))
ids = sorted(r['id'] for r in chg)
print('  ' + ' '.join(ids))
tb = sum(r['bytes_before'] for r in rows)
ta = sum(r['bytes_after'] for r in rows)
print('全部 rows 字节: %d -> %d (Δ%+d)' % (tb, ta, ta - tb))
print('changed=%s skipped_same=%s' % (d['changed'], d['skipped_same']))
for k in ('container_usage', 'containers', 'slots', 'attr_channel'):
    if k in d:
        print('%s = %s' % (k, json.dumps(d[k], ensure_ascii=False)[:600]))
