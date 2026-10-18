# -*- coding: utf-8 -*-
r"""explore1.py — 勘察: 字符集字节分布 / ISO 文件树 / IMG 条目规模"""
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
c = json.load(open(CS, encoding='utf-8'))
codes = c['codes']
pairs = c['pair_of']
print('charset: codes=%d pair_of=%d' % (len(codes), len(pairs)))
cc = sorted(int(v) for v in codes.values())
print('codes 字节: min=0x%02X max=0x%02X n=%d' % (cc[0], cc[-1], len(set(cc))))
print('  codes 是否有 <0x80: %s' % [b for b in cc if b < 0x80][:10])
leads = sorted({v[0] for v in pairs.values()})
trails = sorted({v[1] for v in pairs.values()})
print('pair leads: %s (n=%d)' % (['%02X' % b for b in leads], len(leads)))
print('pair trails: n=%d  min=0x%02X max=0x%02X' % (len(trails), trails[0], trails[-1]))
# trail 落在哪些区间
bands = []
prev = None
st = None
for b in trails:
    if prev is None or b != prev + 1:
        if st is not None:
            bands.append((st, prev))
        st = b
    prev = b
bands.append((st, prev))
print('trail 连续区间: %s' % ', '.join('%02X-%02X' % (a, b) for a, b in bands))
print('lead>=0xAE 的死 pair: %d' % sum(1 for v in pairs.values() if v[0] >= 0xAE))
# 空位
legal = set()
for L in range(0xA1, 0xAE):
    for t in range(0x00, 0x100):
        legal.add((L, t))
used_legal = {tuple(v) for v in pairs.values() if 0xA1 <= v[0] < 0xAE}
print('合法 lead 0xA1..0xAD 的对偶空间 = 13*256 = %d; 已用(仅合法) %d; 空位 %d'
      % (13 * 256, len(used_legal), 13 * 256 - len(used_legal)))
used_94 = {tuple(v) for v in pairs.values() if 0xA1 <= v[0] < 0xAE and 0xA1 <= v[1] <= 0xFE}
print('若 trail 限 0xA1..0xFE: 空间 %d, 已用 %d, 空位 %d'
      % (13 * 94, len(used_94), 13 * 94 - len(used_94)))

# 文本可达字节集
tb = set(range(0x20, 0x7F)) | set(cc) | set(leads) | set(trails)
print('文本可达字节集大小 = %d / 256' % len(tb))
print('不在集合里的字节: %s' % ' '.join('%02X' % b for b in range(256) if b not in tb))
