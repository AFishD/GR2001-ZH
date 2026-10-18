# -*- coding: utf-8 -*-
r"""r71e_charset_dump.py — 导出 1504 可用字集 (人读) ; 并做 r64 对照查询"""
import csv
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
pair = sorted(c['pair_of'])
single = sorted(c['codes'])
have = set(pair) | set(single)

with io.open(os.path.join(HERE, 'r71_charset.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('现役字库 (charset_compiled_zh16.json) 共 %d 字: pair_of %d + codes %d\n'
            % (len(have), len(pair), len(single)))
    f.write('\n--- codes (单字节码 %d 字) ---\n' % len(single))
    f.write(''.join(single) + '\n')
    f.write('\n--- pair_of (%d 字) ---\n' % len(pair))
    for i in range(0, len(pair), 64):
        f.write(''.join(pair[i:i + 64]) + '\n')
print('charset -> %s' % os.path.join(HERE, 'r71_charset.txt'))

# ---- r64 对照: 对每个待改片段, 找出 reduce_map.csv 里同一 id 的相关行 ----
MAP = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r64', 'reduce_map.csv')
rows = list(csv.DictReader(io.open(MAP, encoding='utf-8-sig', newline='')))
byid = {}
for r in rows:
    byid.setdefault(r['条目id'], []).append(r)
print('reduce_map: %d 行, 覆盖 %d 条' % (len(rows), len(byid)))

frag = list(csv.DictReader(io.open(os.path.join(HERE, 'r71_frag.csv'), encoding='utf-8-sig', newline='')))


def norm(s):
    return re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', s or '')


with io.open(os.path.join(HERE, 'r71_r64_hint.txt'), 'w', encoding='utf-8', newline='\n') as f:
    cur = None
    for fr in frag:
        if fr['id'] != cur:
            cur = fr['id']
            f.write('\n' + '#' * 92 + '\n### %s\n' % cur)
        run = fr['run']
        f.write('\n-- 待改 run: %s   (缺 %s)\n' % (run, fr['missing']))
        # 用 run 的最长 4 字子串去找
        hits = set()
        probe = run if len(run) <= 4 else None
        cands = []
        if probe:
            cands = [probe]
        else:
            for k in (6, 5, 4):
                for i in range(0, len(run) - k + 1):
                    cands.append(run[i:i + k])
        for r in byid.get(fr['id'], []):
            a, b = norm(r['原文片段(带上下文)']), norm(r['改后片段(带上下文)'])
            if any(cd in a for cd in cands):
                key = (a, b)
                if key in hits:
                    continue
                hits.add(key)
                f.write('     [r64] %s\n        ->  %s   (%s)\n'
                        % (a.strip(), b.strip(), r['替换了哪些超范围字']))
print('r64 对照 -> %s' % os.path.join(HERE, 'r71_r64_hint.txt'))
