# -*- coding: utf-8 -*-
r"""p08_make_test_csv.py — round42: 生成实验用文本表 (只读 GR_ZH93/text, 写到 r42/csv_in/)

做法:
  ① 定位「M18 定向反步兵地雷」那条 SFXML 条目 (nav_sf6 会走到它的详情页);
  ② 把它的 text_edited 换成**含全部候选图标码**的测试文本 (每码一行 + 编号 + 尾随汉字);
  ③ 其余各表逐字节原样复制 (text_edited == text_zh ⇒ 注入器跳过, 一个字都不改)。
"""
import csv
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402

SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text')
DST = os.path.join(HERE, 'csv_in')
BOX = '图'                       # 尾随「参照字」: 图标画不出来时, 会看到它紧贴在 = 后面

# ── ① 找 M18 条目 ──
target = None
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(SRC, fn), encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r.get('resource') == 'SFXML' and 'M18' in (r.get('text_zh') or '') \
                    and '地雷' in (r.get('text_zh') or ''):
                print('[找到] %s  id=%s  len(text_zh)=%d' % (fn, r['id'], len(r['text_zh'])))
                print('       text_en = %r' % (r.get('text_en') or '')[:70])
                print('       text_zh = %r' % (r['text_zh'][:60]))
                target = (fn, r['id'])
                break
    if target:
        break
assert target, '没找到 M18 条目'
tfn, tid = target

# ── ② 测试文本 ──
TEST = '\n'.join([
    '1={{BTN:E0B1}}' + BOX,
    '2={{BTN:E0B5}}' + BOX,
    '3={{BTN:E0E7}}' + BOX,
    '4={{BTN:E0F1}}' + BOX,
    '5={{BTN:E0B1}}{{BTN:E0B5}}' + BOX,
    '6={{BTN:E0E7}}{{BTN:E0F1}}' + BOX,
])
print()
print('[测试文本] (每个标记后面紧跟一个「%s」当参照):' % BOX)
for ln in TEST.split('\n'):
    print('   %s' % ln)
cs = tcslib.Charset()
b = cs.encode_strict(cs.marks_to_pua(TEST.replace('\n', '{br}')))
print('[编码] %d 字节: %s' % (len(b), ' '.join('%02X' % x for x in b)))

# ── ③ 写实验表 ──
if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)
n_hit = 0
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(SRC, fn), encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    for r in rows:
        if fn == tfn and r['id'] == tid:
            r['text_edited'] = TEST
            n_hit += 1
    with io.open(os.path.join(DST, fn), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n')
        w.writeheader()
        w.writerows(rows)
    print('[写] %-32s %5d 行' % (fn, len(rows)))
# meta 一起复制 (注入器用它做格式校验)
for fn in os.listdir(SRC):
    if fn.endswith('.meta.json'):
        shutil.copy2(os.path.join(SRC, fn), os.path.join(DST, fn))
        print('[写] %s' % fn)
assert n_hit == 1, '改写行数 %d != 1' % n_hit
print()
print('[out] %s' % DST)
