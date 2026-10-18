# -*- coding: utf-8 -*-
"""_dbg_charset.py — 临时调试: 复刻 fa_charset.py 的文本变换, 打印 JSON 解析失败点上下文。"""
import io
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
NEW_PAIRS = [('\u6309', 0xB9, 0xFA), ('\u65f6', 0xB9, 0xFB), ('\u5c0f', 0xB9, 0xFC),
             ('\u51fb', 0xB9, 0xFD), ('\u2715', 0xB9, 0xFE)]
DROP_CODES = [('击', 0xB6), ('小', 0xB7), ('时', 0xB8), ('按', 0xB9)]


def ent_text(ch, b1, b2):
    return '  %s: [\n   %d,\n   %d\n  ],\n' % (json.dumps(ch, ensure_ascii=False), b1, b2)


raw = open(CS, 'rb').read().decode('utf-8')
txt = raw
drop_txt = ''.join('  %s: %d,\n' % (json.dumps(ch, ensure_ascii=False), b) for ch, b in DROP_CODES)
assert txt.count(drop_txt) == 1, txt.count(drop_txt)
txt1 = txt.replace(drop_txt, '', 1)
add_txt = ''.join(ent_text(ch, b1, b2) for ch, b1, b2 in NEW_PAIRS)
anchor = '\n },\n "trim19"'
assert txt1.count(anchor) == 1, txt1.count(anchor)
txt2 = txt1.replace(anchor, ',\n' + add_txt.rstrip('\n') + anchor, 1)
print('len txt1=%d txt2=%d' % (len(txt1), len(txt2)))
try:
    json.loads(txt2)
    print('txt2 解析 OK')
except Exception as e:
    print('txt2 解析失败:', e)
    pos = int(str(e).split('char ')[1].rstrip(')'))
    print('ctx:', repr(txt2[pos - 160:pos + 80]))
    print('AT POS:', repr(txt2[pos - 30:pos]), '<<>>', repr(txt2[pos:pos + 30]))
    for k in range(pos - 4, pos + 4):
        print('   [%d] %r' % (k, txt2[k]))
    print('json.dumps of the 5 keys:', [json.dumps(c, ensure_ascii=False) for c in
                                        ('\u6309', '\u65f6', '\u5c0f', '\u51fb', '\u2715')])
    print('pair_of tail raw:', repr(raw[raw.find('"龄"'):raw.find('"龄"') + 60]))
