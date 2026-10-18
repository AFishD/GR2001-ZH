# -*- coding: utf-8 -*-
r"""remaining_missing.py — 用扩库后的 charset 对「用户原表」跑预检, 列出仍缺的字"""
import csv
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
WRAP_RE = re.compile(r'\{\s*(?:WRAP|WARP)\s*\}', re.I)
BTN_RE = re.compile(r'\{\{BTN:[0-9A-Fa-f]{4}\}\}')


def main():
    cs = json.load(io.open(CS, encoding='utf-8'))
    font = set(cs['codes']) | set(cs['pair_of'])
    print('当前 charset: 单字节 %d + 对偶 %d = %d 字' %
          (len(cs['codes']), len(cs['pair_of']), len(font)))
    rows = list(csv.DictReader(io.open(
        os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text', 'GR_ZH92_text_long.csv'),
        encoding='utf-8-sig')))
    need = {}
    for r in rows:
        t = BTN_RE.sub('', WRAP_RE.sub('', r['text_edited']))
        for ch in t:
            if ord(ch) >= 0x80 and ch not in font:
                need.setdefault(ch, []).append(r['id'])
    print('用户原表里仍缺的非 ASCII 字: %d 个' % len(need))
    for ch, ids in sorted(need.items()):
        print('   %s U+%04X  %d 处: %s' % (ch, ord(ch), len(ids), ', '.join(ids[:5])))

    # 当前盘上实机可用的字 (charset + ASCII)
    print()
    print('=== 用户替代稿里仍缺的字 ===')
    B = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text_fix', 'GR_ZH92_text_long.csv')
    if os.path.isfile(B):
        rows2 = list(csv.DictReader(io.open(B, encoding='utf-8-sig')))
        need2 = {}
        for r in rows2:
            t = BTN_RE.sub('', WRAP_RE.sub('', r['text_edited']))
            for ch in t:
                if ord(ch) >= 0x80 and ch not in font:
                    need2.setdefault(ch, []).append(r['id'])
        print('   仍缺: %d 个 %s' % (len(need2), ''.join(sorted(need2)) or '(无)'))


if __name__ == '__main__':
    main()
