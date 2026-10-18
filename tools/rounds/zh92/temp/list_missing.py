# -*- coding: utf-8 -*-
r"""list_missing.py — 列出用户译文里字库没有的字 (预检报告的摘要)"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PY = sys.executable
REPORT = os.path.join(HERE, 'precheck_report.json')

r = subprocess.run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
                    '--csv', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text'),
                    '--src', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'),
                    '--dst', os.path.join(HERE, 'never_written.iso'),
                    '--check-only', '--report', REPORT],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('exit =', r.returncode)
rep = json.load(io.open(REPORT, encoding='utf-8'))
pre = rep.get('charset_precheck') or {}
chars = pre.get('chars') or []
print('问题字符数:', len(chars))
by_kind = {}
for c in chars:
    by_kind.setdefault(c['kind'], []).append(c)
for k, v in by_kind.items():
    print('\n===== %s (%d 个) =====' % (k, len(v)))
    for c in sorted(v, key=lambda x: x['cp']):
        ids = sorted({h['id'] for h in c['hits']})
        print('  %-3s U+%04X  %-28s 出现 %d 处: %s'
              % (c['char'], c['cp'], (c.get('reason') or '')[:28], len(c['hits']),
                 ', '.join(ids[:4]) + (' …' if len(ids) > 4 else '')))
