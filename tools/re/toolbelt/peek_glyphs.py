# -*- coding: utf-8 -*-
r"""peek_glyphs.py — 看构建任务 glyphs_zh120.json 的汇总与「嘚」的处理"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r81\glyphs_zh120.json'
d = json.load(open(p, encoding='utf-8'))
for k in ('source', 'total', 'ok', 'ttf_missing', 'overflow'):
    v = d.get(k)
    print('  %-12s = %s' % (k, json.dumps(v, ensure_ascii=False)[:200]))
items = d.get('items', [])
print('  items 类型 %s 长度 %s' % (type(items).__name__, len(items) if hasattr(items, '__len__') else '?'))
if isinstance(items, list) and items:
    print('  样例 item:', json.dumps(items[0], ensure_ascii=False)[:220])
    hit = 0
    for it in items:
        s = json.dumps(it, ensure_ascii=False)
        if '561A' in s.upper() or '561a' in s:
            print('  ★ 缺字项:', s[:300])
            hit += 1
    if not hit:
        print('  ★ items 里没有 561A 的单独项（可能它只列成功渲出的 363 个）')
        # 看是否有 code 字段
        ks = set()
        for it in items[:50]:
            if isinstance(it, dict):
                ks |= set(it.keys())
        print('  item 字段:', sorted(ks))
if isinstance(d.get('ttf_missing'), list):
    print('  ttf_missing 明细:', json.dumps(d['ttf_missing'], ensure_ascii=False)[:400])
if isinstance(d.get('overflow'), list):
    print('  overflow 明细:', json.dumps(d['overflow'], ensure_ascii=False)[:400])
