# -*- coding: utf-8 -*-
"""r50: 占位符 / 控制标记 / 符号 的全量清单 (给文档与报告用)。"""
import collections
import csv
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                             # noqa: E402
import icon_table                                         # noqa: E402

TD = os.path.join(REPO, 'work/builds/GR_ZH98/text')
INJ = [f for f in sorted(os.listdir(TD)) if f.endswith('.csv') and '_text_' in f]
BTN = re.compile(r'\{\{BTN:([0-9A-Fa-f]{4})\}\}', re.I)
CTRL = re.compile(r'\{(br|p|WRAP|Warp|wrap)\}', re.I)

btn = collections.Counter()
ctrl = collections.Counter()
chars = collections.Counter()
files = collections.Counter()
for fn in INJ:
    with io.open(os.path.join(TD, fn), encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        for row in rd:
            blob = ''
            for col in ('text_edited', 'text_zh', 'text_en'):
                blob += (row.get(col) or '')
            for m in BTN.finditer(blob):
                btn['%04X' % int(m.group(1), 16)] += 1
                files[fn] += 1
            for m in CTRL.finditer(blob):
                ctrl[m.group(1).upper()] += 1
            for ch in blob:
                chars[ch] += 1
print('== 注入表 %d 张: %s' % (len(INJ), ', '.join(INJ)))
print('== {{BTN:XXXX}} 标记用量: %s' % dict(btn))
print('== 控制标记用量: %s' % dict(ctrl))
print()
cs = tcslib.Charset()
print('== charset: 单字节码 %d 个, 对偶码 %d 个' % (len(cs.enc_single), len(cs.enc_pair)))
han = [c for c in cs.enc_single if '\u4e00' <= c <= '\u9fff']
lat = [c for c in cs.enc_single if not ('\u4e00' <= c <= '\u9fff')]
print('   单字节码里的汉字 %d 个: %s' % (len(han), ''.join(sorted(han))))
print('   单字节码里的非汉字 %d 个: %s' % (len(lat), ' '.join('%s=%02X' % (c, cs.enc_single[c])
                                                            for c in sorted(lat, key=lambda x: cs.enc_single[x]))))
spec = [(c, cs.enc_pair[c]) for c in cs.enc_pair if not ('\u4e00' <= c <= '\u9fff')]
print('   对偶码里的非汉字 %d 个:' % len(spec))
for c, p in sorted(spec, key=lambda kv: tcslib.pair_slot(*kv[1])):
    print('      %s = %02X%02X  slot=%4d  正文用量=%d' % (c, p[0], p[1],
                                                          tcslib.pair_slot(*p), chars.get(c, 0)))
print()
print('== 引擎认的文本图标码:')
for r in icon_table.all_icons():
    print('   %s = 0x%02X %s  UV=%s' % (tcslib.BTN_FMT % r['pua'], r['byte'], r['name'], r['uv']))
print('== 未映射/非图标字节:')
for b, r in sorted(icon_table.NOT_ICON_CODES.items()):
    print('   0x%02X = Latin-1 %s (%s)' % (b, r['latin1'], r['name']))
print()
print('== 疑似"占位符"但其实是真字的候选 (正文用量 > 0):')
for ch in '±®µ蹚':
    print('   %s  单字节=%s 对偶=%s  用量=%d'
          % (ch, cs.enc_single.get(ch), cs.enc_pair.get(ch), chars.get(ch, 0)))
