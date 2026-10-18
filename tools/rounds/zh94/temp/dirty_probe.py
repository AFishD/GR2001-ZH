# -*- coding: utf-8 -*-
r"""dirty_probe.py — 查 中/抖 的码位与图集格, 对比 GR_ZH93 vs GR_ZH94 找污染来源"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
cs = json.load(io.open(CS, encoding='utf-8'))
codes = cs['codes']
pairs = cs['pair_of']

for ch in ('中', '抖', '毕'):
    print('=== %s ===' % ch)
    if ch in codes:
        b = codes[ch]
        print('  单字节码 0x%02X' % b)
        # 单字节走 FT 记录矩形; 找 idx = code-0x20
        print('  FT 记录 idx = %d (=0x%02X-0x20)' % (b - 0x20, b))
    if ch in pairs:
        b1, b2 = pairs[ch]
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        r, c = slot // 62, slot % 62
        print('  对偶码 %02X %02X  slot=%d  row=%d col=%d' % (b1, b2, slot, r, c))
        print('  引擎格 (x,y) = (%d, %d)  ⇒ 该格 x..x+15, y..y+15' % (x, y))
        print('  是否"回绕列"(col 接近 63)? col=%d, x+16=%d (图集宽 1024)' % (c, x + 16))
    print()

# 看 FT 记录表里 中/抖 的记录矩形
FT = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'font', 'GR_ZH94_font_ft.csv')
if os.path.isfile(FT):
    import csv
    rows = list(csv.DictReader(io.open(FT, encoding='utf-8-sig')))
    print('=== FT 记录表 (544 条) 里与 中/抖 的码位对应的记录 ===')
    for ch in ('中', '抖'):
        b = codes.get(ch)
        if b is None:
            continue
        idx = b - 0x20
        hit = [r for r in rows if int(r['index']) == idx and r['has_ink'] in ('1', 'True', 'true')]
        for r in hit:
            print('  %s (0x%02X, idx=%d): face=%s 矩形 u=%s..%s v=%s..%s 墨=%s'
                  % (ch, b, idx, r['face'], r['u0'], r['u1'], r['v0'], r['v1'], r['ink_px']))
