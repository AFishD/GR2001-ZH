# -*- coding: utf-8 -*-
"""核对 §8.7: 旧 charset 里 lead ≥ 0xAE 的对偶字有多少、是否在用、重排后落在哪。"""
import csv
import io
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402

old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                  'charset_before_r56.json'))
new = tcslib.Charset()
oc = [ch for ch, (b1, b2) in old.enc_pair.items() if b1 >= 0xAE]
print('旧 charset: 对偶字 %d 个; 其中 lead ≥ 0xAE 的 **%d 个**' % (len(old.enc_pair), len(oc)))
print('  这些字:', ''.join(oc))
print('  旧码位:', ' '.join('%02X%02X' % old.enc_pair[c] for c in oc))
print('  旧 slot:', sorted(tcslib.pair_slot(*old.enc_pair[c]) for c in oc))
print('  新码位:', ' '.join('%02X%02X' % new.enc_pair[c] for c in oc))
ns = sorted(tcslib.pair_slot(*new.enc_pair[c]) for c in oc)
print('  新 slot: %d..%d (lead 全部 ≤ 0x%02X)' % (ns[0], ns[-1], max(new.enc_pair[c][0] for c in oc)))
# 新 charset 里还有没有 lead ≥ 0xAE 的对偶字?
n2 = [ch for ch, (b1, b2) in new.enc_pair.items() if b1 >= 0xAE]
print('  新 charset 里 lead ≥ 0xAE 的字: %d 个 %s' % (len(n2), ''.join(n2)))
# 这些字在正文里用到了吗?
occ = {}
for fn in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text'))):
    if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
        with io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text', fn),
                     encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                for ch in (row.get('text_edited') or ''):
                    occ[ch] = occ.get(ch, 0) + 1
used = [(c, occ.get(c, 0)) for c in oc]
print('  在 GR_ZH105 正文里的出现次数: 用到 %d 个, 合计 %d 字次'
      % (sum(1 for _c, n in used if n), sum(n for _c, n in used)))
print('  明细:', ' '.join('%s×%d' % (c, n) for c, n in used if n))
