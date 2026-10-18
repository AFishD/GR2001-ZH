# -*- coding: utf-8 -*-
r"""p15_show_summary.py — 打印 _font_summary.json 的 capacity / grid_selfcheck 段 (人话)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else 'run1',
                 'GR_ZH93_font_summary.json')
d = json.load(io.open(P, encoding='utf-8'))
print('文件: %s' % os.path.relpath(P, os.path.abspath(os.path.join(HERE, '..', '..', '..',
                                                                   '..', '..'))))
print('\n===== capacity.pair =====')
for k, v in d['capacity']['pair'].items():
    s = str(v)
    print('  %-24s = %s' % (k, s if len(s) <= 150 else s[:150] + '…'))
print('\n===== capacity.single =====')
for k, v in d['capacity']['single'].items():
    s = str(v)
    print('  %-24s = %s' % (k, s if len(s) <= 150 else s[:150] + '…'))
print('\n===== capacity.charset / atlas / verdict =====')
for sec in ('charset', 'atlas', 'verdict'):
    for k, v in d['capacity'][sec].items():
        s = str(v)
        print('  %-24s = %s' % (k, s if len(s) <= 150 else s[:150] + '…'))
print('\n===== grid_selfcheck =====')
for k, v in d['grid_selfcheck'].items():
    print('  %-24s = %s' % (k, v))
print('\n===== grid =====')
for k, v in d['grid'].items():
    print('  %-24s = %s' % (k, v))
print('\n===== counts =====')
for k, v in d['counts'].items():
    print('  %-24s = %s' % (k, v))
