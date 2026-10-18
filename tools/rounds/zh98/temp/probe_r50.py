# -*- coding: utf-8 -*-
r"""probe_r50.py — ① 孙/宁/宇 底端截断 ② ± 的角色 ③ tcslib 锚点现状"""
import csv
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
cs = json.load(io.open(CS, encoding='utf-8'))
pair_of = cs['pair_of']
codes = cs['codes']

print('=' * 72)
print('① 孙 / 宁 / 宇 的码位与引擎格 (当前 charset = GR_ZH98, 已回收 144 字)')
print('=' * 72)
for ch in ('孙', '宁', '宇'):
    if ch in pair_of:
        b1, b2 = pair_of[ch]
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        print('  %s : 对偶码 %02X %02X  slot=%d  row=%d col=%d  引擎格=(%d,%d)' %
              (ch, b1, b2, slot, slot // 62, slot % 62, x, y))
    elif ch in codes:
        print('  %s : 单字节码 0x%02X' % (ch, codes[ch]))
    else:
        print('  %s : **不在当前 charset** (可能已被回收)' % ch)

# 看回收备份里有没有
bk = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'font_recycle_backup.json')
if os.path.isfile(bk):
    b = json.load(io.open(bk, encoding='utf-8'))
    chars = b.get('chars') or b.get('removed_chars') or []
    if isinstance(chars, str):
        chars = list(chars)
    print('  回收备份里共 %d 字; 孙/宁/宇 在内? %s' %
          (len(chars), [c for c in ('孙', '宁', '宇') if c in chars]))
    # 打印备份结构
    print('  备份键:', list(b.keys())[:8])

print()
print('=' * 72)
print('② ± 在 charset / 文本里的角色')
print('=' * 72)
print('  charset.codes 里有没有 ± :', '±' in codes, ('0x%02X' % codes['±']) if '±' in codes else '')
print('  charset.pair_of 里有没有 ± :', '±' in pair_of)
# 找所有"非汉字"的映射
odd = [(ch, 'single 0x%02X' % codes[ch]) for ch in codes if not ('\u4e00' <= ch <= '\u9fff')]
print('  codes 里的非汉字 (%d 个): %s' % (len(odd), ', '.join('%s=%s' % kv for kv in sorted(odd, key=lambda kv: kv[1]))))
odd2 = [ch for ch in pair_of if not ('\u4e00' <= ch <= '\u9fff')]
print('  pair_of 里的非汉字 (%d 个): %s' % (len(odd2), ''.join(odd2)))
# 文本表里 ± 出现情况
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text')
n_tot = 0
samples = []
for n in sorted(os.listdir(TDIR)):
    if not n.endswith('.csv'):
        continue
    for r in csv.DictReader(io.open(os.path.join(TDIR, n), encoding='utf-8-sig')):
        for col in ('text_edited', 'text_zh', 'text_en'):
            t = r.get(col) or ''
            if '±' in t:
                n_tot += 1
                if len(samples) < 6:
                    i = t.find('±')
                    samples.append('%s/%s[%s]: …%s…' % (n.replace('GR_ZH98_text_', '').replace('.csv', ''),
                                                        r.get('id'), col, t[max(0, i - 18):i + 18]))
                break
print('  文本表里含 ± 的行: %d' % n_tot)
for s in samples:
    print('    ', s)
# 类似的占位符: {{BTN:xxxx}} 与 {xx}
print('  {{BTN:…}} 出现行数 (前 3 表抽样):')
nb = 0
for n in sorted(os.listdir(TDIR)):
    if not n.endswith('.csv'):
        continue
    for r in csv.DictReader(io.open(os.path.join(TDIR, n), encoding='utf-8-sig')):
        if '{{BTN:' in (r.get('text_edited') or '') or '{{BTN:' in (r.get('text_zh') or ''):
            nb += 1
print('    %d 行' % nb)

print()
print('=' * 72)
print('③ tcslib 里的硬编码锚点')
print('=' * 72)
src = io.open(os.path.join(REPO, 'tools', 'text_csv', 'tcslib.py'), encoding='utf-8').read().splitlines()
for i, l in enumerate(src, 1):
    if 'AF' in l and ('A1' in l or 'BD' in l) or 'selfcheck_charset' in l or '锚点' in l or 'anchor' in l.lower():
        print('  L%d: %s' % (i, l.rstrip()[:130]))
