# -*- coding: utf-8 -*-
r"""show_blocker.py — 精确列出当前预检里"阻断级"的问题字符"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
                    '--csv', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text'),
                    '--src', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'),
                    '--dst', os.path.join(HERE, 'never2.iso'), '--check-only'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
out = (r.stdout or '') + (r.stderr or '')
print('exit =', r.returncode)
print('--- 阻断级问题行 ---')
for ln in out.splitlines():
    s = ln.strip()
    if ('字符集' in s and '没有' in s) or '死 pair' in s or '字形' in s and '没有' in s:
        print('   ', s[:160])
print('--- 含 "U+" 且不含 "不阻断" 的行 ---')
for ln in out.splitlines():
    if 'U+' in ln and '不阻断' not in ln and '仅提示' not in ln:
        print('   ', ln.strip()[:160])
print('--- 结尾结论 ---')
for ln in out.splitlines():
    if '预检不通过' in ln or '预检通过' in ln or 'verdict' in ln:
        print('   ', ln.strip()[:160])
