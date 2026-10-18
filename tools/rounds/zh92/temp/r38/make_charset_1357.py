# -*- coding: utf-8 -*-
r"""make_charset_1357.py — 从「字库 dump CSV」重建 **Lead 那一版** charset (1357 字)

为什么需要: 另一个子代理正在扩字库 (现役 charset 已从 1357 字涨到 1433 字),
所以"70 缺字 / 145 闲置"这组数字必须**钉在同一个 charset 版本**上才能交叉验证。

work/builds/GR_ZH92/font/GR_ZH92_font_charset.csv 是构筑时留下的字库快照 (只读),
含 char/unicode/kind/bytes_hex/slot/cell_x/cell_y —— 足以逐字节重建 codes + pair_of。

★ 顺带做一次**独立交叉验证**: CSV 里的 slot / cell_x / cell_y 必须与
  font_usage.slot_cell() 的公式逐位一致 (否则本工具的格位算法就是错的)。
"""
import csv
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
import font_usage as F  # noqa: E402

SRC = os.path.join(REPO, 'work/builds/GR_ZH92/font/GR_ZH92_font_charset.csv')
LIVE = os.path.join(REPO, 'tools/font_pipeline/data/charset_compiled_zh16.json')
OUT = os.path.join(REPO, 'work/builds/GR_ZH92/temp/r38/charset_from_fontdump_1357.json')

rows = list(csv.DictReader(io.open(SRC, encoding='utf-8-sig')))
print('# 字库 dump CSV: %d 行' % len(rows))
kinds = {}
for r in rows:
    kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
print('# kind 分布: %s' % kinds)

codes, pair_of = {}, {}
bad = []
for r in rows:
    k = r['kind']
    if k not in ('single', 'pair'):
        continue
    ch = r['char']
    b = bytes.fromhex(r['bytes_hex'].strip())
    if k == 'single':
        assert len(b) == 1, (ch, r['bytes_hex'])
        codes[ch] = b[0]
    else:
        assert len(b) == 2, (ch, r['bytes_hex'])
        pair_of[ch] = [b[0], b[1]]
    # ★ 独立验证格位公式
    if k == 'pair' and r['slot'].strip():
        slot = int(r['slot'])
        x, y = F.slot_cell(slot)
        if slot != F.pair_slot((b[0], b[1])) or (x, y) != (int(r['cell_x']), int(r['cell_y'])):
            bad.append((ch, r['bytes_hex'], slot, (x, y), r['cell_x'], r['cell_y']))

print('# 重建: codes %d + pair_of %d = %d 字' % (len(codes), len(pair_of),
                                              len(codes) + len(pair_of)))
print('# ★ 格位公式交叉验证 (与字库 dump 的 slot/cell_x/cell_y 逐位比对): '
      '%s' % ('[ok] 全部一致 ✓ (%d 个对偶字)' % len(pair_of) if not bad
              else '[!!] %d 个不一致: %s' % (len(bad), bad[:5])))
assert not bad, '格位公式与字库 dump 不一致!'

live = json.load(io.open(LIVE, encoding='utf-8'))
out = dict(live)
out['codes'] = codes
out['pair_of'] = pair_of
out['_reconstructed_from'] = os.path.relpath(SRC, REPO).replace('\\', '/')
out['_note'] = ('由 work/builds/GR_ZH92/font/GR_ZH92_font_charset.csv 重建的 **构筑期** charset; '
                '只用于交叉验证 Lead 的 1357 字口径, 不是现役表')
out['grid'] = dict(live['grid'])
io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('# -> %s' % os.path.relpath(OUT, REPO))

# 与现役表比对
now = json.load(io.open(LIVE, encoding='utf-8'))
print('# 现役表: codes %d + pair_of %d = %d 字'
      % (len(now['codes']), len(now['pair_of']), len(now['codes']) + len(now['pair_of'])))
added_c = sorted(set(now['codes']) - set(codes))
added_p = sorted(set(now['pair_of']) - set(pair_of))
removed_c = sorted(set(codes) - set(now['codes']))
removed_p = sorted(set(pair_of) - set(now['pair_of']))
print('# 现役比构筑期多: 单字节 %d 个 %s' % (len(added_c), ''.join(added_c[:60])))
print('#                 对偶   %d 个 %s' % (len(added_p), ''.join(added_p[:60])))
print('# 现役比构筑期少: 单字节 %d / 对偶 %d %s'
      % (len(removed_c), len(removed_p), ''.join(removed_c[:20]) + ''.join(removed_p[:20])))
# 映射是否被改动 (这是"扩字库有没有动到老字"的关键问题)
moved = [ch for ch in set(codes) & set(now['codes']) if codes[ch] != now['codes'][ch]]
moved += [ch for ch in set(pair_of) & set(now['pair_of'])
          if pair_of[ch] != now['pair_of'][ch]]
print('# ★ 老字码位被改动的: %d 个 %s' % (len(moved), ''.join(moved[:40])))
