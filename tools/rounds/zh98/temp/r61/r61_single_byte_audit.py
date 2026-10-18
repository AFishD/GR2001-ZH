# -*- coding: utf-8 -*-
r"""r61_single_byte_audit.py — 单字节码审计: 测试页里"新出现"的那些字节, 在**已交付文本**里到底用不用?

背景 (r61_page_bytes.py 的结果):
  · 编码是**混合 1/2 字节**: 有些字是单字节码 (例: 「一」= 0xB7, 原文第一行里就是它),
    另一些是对偶码。所以"单字节码"本身合法。
  · 但测试页新引入了 0x80..0xA0 这 33 个字节 + 0xFF, 而**原版那一页一个都没用**。
  · 若这些码值在整份已交付文本里**从未出现**, 它们就是"只有测试页才用过"的码位 ⇒
    引擎/字库对它们的支持从未被验证过, 是"整页空白"的头号嫌疑。

用法: python work/builds/GR_ZH98/temp/r61/r61_single_byte_audit.py
"""
import collections
import csv
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

cs = T.Charset()
b2c = {bb: ch for ch, bb in cs.enc_single.items()}
single_bytes = sorted(b2c)
SUSPECT = [b for b in single_bytes if b <= 0xA0 or b == 0xFF]

print('单字节码 %d 个; 其中"可疑"(<=0xA0 或 0xFF) %d 个' % (len(single_bytes), len(SUSPECT)))
print('  可疑码值 -> 字符:')
print('   ', ' '.join('%02X=%s' % (b, b2c[b]) for b in SUSPECT))

# ---- 语料: 已交付版本的全部文本 (CSV 的 text_zh / text_edited 是盘上意图文本) ----
tables = sorted(glob.glob(os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text',
                                       'GR_ZH109_text_*.csv')))
cnt = collections.Counter()
rows = 0
for p in tables:
    if '_view_' in p:
        continue
    with io.open(p, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            rows += 1
            for col in ('text_edited', 'text_zh'):
                t = row.get(col) or ''
                if not t:
                    continue
                for ch in t:
                    bb = cs.enc_single.get(ch)
                    if bb is not None:
                        cnt[bb] += 1
print('\n语料 = %s (%d 行)' % ([os.path.basename(p) for p in tables], rows))
print('语料里单字节码总出现次数 = %d' % sum(cnt.values()))
used = sorted(cnt)
print('  语料用到的单字节码 (%d 个): %s' % (len(used), ['%02X' % b for b in used]))
print('\n★ 可疑码在语料里的出现次数:')
never = []
for b in SUSPECT:
    c = cnt.get(b, 0)
    if c == 0:
        never.append(b)
    print('    %02X (%s): %d 次' % (b, b2c[b], c))
print('\n★★ 语料里**从未出现**的可疑码 %d 个: %s' % (len(never), ['%02X' % b for b in never]))
print('   => 这些码位在已交付文本里没有任何先例; 测试页是第一次使用它们。')
print('   字符: %s' % ''.join(b2c[b] for b in never))
return_none = None
