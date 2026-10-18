# -*- coding: utf-8 -*-
r"""r71i_state.py — 只抽取需要的字段: 各版本构筑状态 + GR_ZH113 字库槽位状态"""
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(p):
    return json.load(io.open(p, encoding='utf-8'))


print('=== 各版本 build_info 概要 ===')
for v in ('GR_ZH111', 'GR_ZH113', 'GR_ZH114', 'GR_ZH115', 'GR_ZH116', 'GR_ZH117'):
    p = os.path.join(REPO, 'work', 'builds', v, 'build_info.json')
    if not os.path.exists(p):
        print('  %-10s <无 build_info>' % v)
        continue
    d = load(p)
    fc = d.get('font_compact') or {}
    print('  %-10s base=%-28s patch=%-40s font_step=%-14s built=%s'
          % (v, (d.get('base') or '-').replace('work/builds/', ''),
             (d.get('patch') or '-').replace('tools/iso_build/', ''),
             d.get('font_step_tool') or '-', d.get('built')))
    if fc:
        print('             font_compact: changed=%s kept=%s used=%s free=%s usable=%s record=%s gate_ok=%s'
              % (fc.get('changed'), fc.get('kept'), fc.get('used'), fc.get('free_slots'),
                 fc.get('usable_cells'), fc.get('record_cells'), fc.get('gate_ok')))

print()
print('=== GR_ZH113 字库 dump 概要 ===')
p = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'font', 'GR_ZH113_font_summary.json')
d = load(p)
print('  顶层键:', list(d.keys()))
for k in ('iso_sha256', 'atlas', 'grid', 'ft', 'charset', 'counts', 'summary'):
    if k in d:
        v = d[k]
        s = json.dumps(v, ensure_ascii=False)
        print('  %s = %s' % (k, s[:600]))
