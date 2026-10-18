# -*- coding: utf-8 -*-
r"""lead_sfxml_safety.py — 独立复核: SFXML 修复是否只动了 name= 属性, <text> 正文一字未动

比对 GR_ZH98 (修前) 与 GR_ZH101 (修后):
  · <text> 正文区的字节序列
  · 每个 name= 属性的字节 (应只有 49 条被改, 且长度不变)
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import repack_leak_scan as R                            # noqa: E402

CS = R.tcslib.Charset(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                   'charset_compiled_zh16.json'))
PAIRS = [('GR_ZH98(修前)', 'work/builds/GR_ZH98/GR_ZH98.iso'),
         ('GR_ZH101(修后)', 'work/builds/GR_ZH101/GR_ZH101.iso')]

res = {}
for tag, rel in PAIRS:
    iso = R.tcslib.Iso(os.path.join(REPO, rel))
    blob = R.load_blob(iso, 'SFXML')['blob']
    attrs = R.sfxml_attributes(blob, CS)
    texts = R.sfxml_text_elements(blob)
    res[tag] = dict(blob=blob, attrs=attrs, texts=texts)
    print('%-14s SFXML %d 字节; name 属性 %d; <text> 匹配 %s 对, 正文 %s 字节'
          % (tag, len(blob), len(attrs), texts['matched_pairs'], texts['bytes']))

a, b = res['GR_ZH98(修前)'], res['GR_ZH101(修后)']

# ① <text> 正文是否一字未动
ta = [x['bytes_hex'] if isinstance(x, dict) and 'bytes_hex' in x else str(x) for x in [a['texts']]]
tb = [x['bytes_hex'] if isinstance(x, dict) and 'bytes_hex' in x else str(x) for x in [b['texts']]]
print()
print('① <text> 统计相同:', json.dumps(a['texts'], ensure_ascii=False) == json.dumps(b['texts'], ensure_ascii=False))
print('   A:', json.dumps(a['texts'], ensure_ascii=False)[:200])
print('   B:', json.dumps(b['texts'], ensure_ascii=False)[:200])

# ② name 属性逐条对比
ka = {(x['tag'], x['off']): x for x in a['attrs']}
kb = {(x['tag'], x['off']): x for x in b['attrs']}
same = changed = added = removed = 0
len_changed = 0
for k in set(ka) | set(kb):
    if k not in ka:
        added += 1
        continue
    if k not in kb:
        removed += 1
        continue
    if ka[k]['bytes_hex'] == kb[k]['bytes_hex']:
        same += 1
    else:
        changed += 1
        if ka[k]['nbytes'] != kb[k]['nbytes']:
            len_changed += 1
print()
print('② name 属性: 相同 %d ; **被改 %d** ; 新增 %d ; 删除 %d ; 其中长度变化 %d'
      % (same, changed, added, removed, len_changed))
print('   被改的属性长度是否全部不变:', '✓' if len_changed == 0 else '✗')

# ③ 展示前 6 条被改的属性 (旧 → 新, 用当前 charset 解出)
pm, sm = {}, dict(CS.codes)
for ch, (b1, b2) in CS.pair_of.items():
    pm[(b1, b2)] = ch
n = 0
for k in sorted(set(ka) & set(kb)):
    if ka[k]['bytes_hex'] == kb[k]['bytes_hex']:
        continue
    ra = bytes.fromhex(ka[k]['bytes_hex'].replace(' ', ''))
    rb = bytes.fromhex(kb[k]['bytes_hex'].replace(' ', ''))
    print('   %-8s %-14s  旧 %-30s → 新 %s'
          % (k[0], ka[k]['text'][:12], R.decode_with(pm, sm, ra), R.decode_with(pm, sm, rb)))
    n += 1
    if n >= 6:
        break
