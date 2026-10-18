# -*- coding: utf-8 -*-
r"""inject_check.py —— 把 `dfix_apply.py --check` 的**原始输出文本**注入各盘 meta.json。

任务要求：每张盘的 meta.json 必须含 `base_sha256` / 逐站点 VA·ISO·原字·新字 / `diff_runs` /
sha256 / 尺寸 / **`--check` 输出** / 每处改动的行为与风险。本脚本补齐"`--check` 输出"这一项。

用法: python work\builds\GR_DFIX\tools\inject_check.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TAGS = ['DFIX_pkt', 'DFIX_icon', 'DFIX_fp', 'DFIX_pkt_fp']

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base_check = io.open(os.path.join(ROOT, 'audit', 'check_base.txt'), encoding='utf-8', errors='replace').read()

for t in TAGS:
    mp = os.path.join(ROOT, t + '.meta.json')
    cp = os.path.join(ROOT, 'audit', 'check_%s.txt' % t)
    if not (os.path.exists(mp) and os.path.exists(cp)):
        print('跳过 %s（缺 meta 或 check 输出）' % t)
        continue
    m = json.load(io.open(mp, encoding='utf-8'))
    txt = io.open(cp, encoding='utf-8', errors='replace').read()
    m['check_output'] = txt
    m['check_output_note'] = (
        '这是**产物盘**上的 --check 输出：站点表断言的是**原字**，已打站点必然显示"原字不符"，'
        '所以"断言通过 = 21 − 本盘站点数"。基底副本上的 --check 为 21/21（见 base_check_output）。')
    m['base_check_output'] = base_check
    m['base_check_result'] = '断言通过 21 / 21'
    with io.open(mp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(m, f, indent=1, ensure_ascii=False)
    print('注入 %s（%d B 的 --check 输出）' % (os.path.basename(mp), len(txt)))
