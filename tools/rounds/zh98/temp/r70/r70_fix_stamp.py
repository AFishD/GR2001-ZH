# -*- coding: utf-8 -*-
r"""r70_fix_stamp.py — 把 charset 的 _font_compact 戳修正成有意义的标签

背景: 我用 `make_build.py GR_TEST_RESTAMP/GR_TEST_RESTAMP2 --from GR_ZH113` 跑默认构筑
来验证"网格占满后默认构筑可用", 这一步把戳里的 iso_version 写成了临时名
`GR_TEST_RESTAMP2`, 且 used/free_slots 沿用了 0 改动路径的旧值(1175/1175..1503)。

功能字段 iso_sha256 是对的(= GR_ZH113 的 da19dac4…), 只修标签与统计, 不动映射。
"""
import io
import json
import sys

P = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\tools\font_pipeline\data\charset_compiled_zh16.json'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(P, encoding='utf-8'))
fc = c.get('_font_compact') or {}
print('修正前: iso_version=%s used=%s free_slots=%s' %
      (fc.get('iso_version'), fc.get('used'), fc.get('free_slots')))

n_pair = len(c['pair_of'])
fc['iso_version'] = 'GR_ZH113'
fc['used'] = n_pair
fc['free_slots'] = None                       # 网格已占满(1504/1504)
fc['note_stamp_fix'] = ('round70: iso_version 原被临时验证盘名覆盖(GR_TEST_RESTAMP2); '
                        'used/free_slots 是 0 改动路径沿用的旧值。功能字段 iso_sha256 未变。')
c['_font_compact'] = fc

io.open(P, 'w', encoding='utf-8').write(json.dumps(c, ensure_ascii=False, indent=1))
print('修正后: iso_version=%s used=%s free_slots=%s' % (fc['iso_version'], fc['used'], fc['free_slots']))

# 回读校验: 映射必须一字节不变
c2 = json.load(io.open(P, encoding='utf-8'))
assert len(c2['pair_of']) == n_pair and len(c2['codes']) == len(c['codes']), '映射变了!'
assert c2['pair_of'] == c['pair_of'] and c2['codes'] == c['codes'], '映射变了!'
print('回读: pair_of %d / codes %d 映射逐项相同 ✓' % (len(c2['pair_of']), len(c2['codes'])))
