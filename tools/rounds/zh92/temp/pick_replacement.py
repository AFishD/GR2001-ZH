# -*- coding: utf-8 -*-
r"""pick_replacement.py — 从字库实际拥有的字里, 为「结构脆弱问处」挑一个成立的替代"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
cs = json.load(io.open(CS, encoding='utf-8'))
font = set(cs['codes']) | set(cs['pair_of'])

CANDS = ['等缺陷', '等短板', '等隐患', '等状况', '等因素', '等不足', '等弊病', '等漏洞',
         '等缺点', '等瑕疵', '等故障', '等情形', '等毛病', '等问题', '与缺陷', '方面的不足']
print('候选替代 (整段: 因存在诸多可靠性与结构脆弱<X>，促使美军…)')
for c in CANDS:
    bad = [ch for ch in c if ord(ch) >= 0x80 and ch not in font]
    print('   %-8s %s' % (c, '✓ 可用' if not bad else '✗ 缺: ' + ''.join(bad)))

print()
print('整句候选 (整句替换, 逐字校验):')
SENTS = [
    '因存在诸多可靠性与结构脆弱等不足',
    '因存在诸多可靠性与结构脆弱等缺陷',
    '因存在诸多可靠性与结构脆弱等因素',
    '因存在诸多可靠性与结构脆弱等状况',
]
for s in SENTS:
    bad = [ch for ch in s if ord(ch) >= 0x80 and ch not in font]
    print('   %s  %s' % (s, '✓' if not bad else '✗ 缺: ' + ''.join(bad)))
