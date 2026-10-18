# -*- coding: utf-8 -*-
"""r51 探针⑩: 找出「何为幽灵？」标题在盘上的**真实归属** (T0062/T0063 ...)。只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

cs = tcslib.Charset()
p = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text', 'GR_ZH98_text_long.csv')
for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')):
    if r['resource'] != 'SFXML':
        continue
    if not (r['id'] >= 'SFXML:T0058' and r['id'] <= 'SFXML:T0068'):
        continue
    print('=' * 90)
    print('id=%s off=%s len=%s kind=%s wrap_w=%s lines=%s'
          % (r['id'], r['offset'], r['len_bytes'], r['kind'], r['wrap_w'], r['lines']))
    for k in ('text_en', 'text_zh', 'text_edited'):
        v = r.get(k) or ''
        print('  %-12s (%d 字): %r' % (k, len(v), v[:260]))
    # 盘上字节
    zh = r.get('text_zh') or ''
    try:
        b = cs.encode_strict(zh.replace('\n', '\x00')) if zh else b''
    except Exception as e:                                                # noqa: BLE001
        b = b''
        print('   encode 失败: %s' % e)
    print('  bytes_zh    : %s' % b.hex(' ')[:400])
