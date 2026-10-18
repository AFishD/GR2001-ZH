# -*- coding: utf-8 -*-
"""charset 细节: codes/pair_of 重叠、常量区间、encode_strict 行为。"""
import io
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402

print('LEAD_LO=%02X LEAD_HI=%02X PAIR_LEAD_LO=%02X PAIR_LEAD_HI=%02X'
      % (tcslib.LEAD_LO, tcslib.LEAD_HI, tcslib.PAIR_LEAD_LO, tcslib.PAIR_LEAD_HI))
print('BTN_LO=%04X BTN_HI=%04X PUA_BASE=%04X' % (tcslib.BTN_LO, tcslib.BTN_HI,
                                                 tcslib.Charset.PUA_BASE))
print('pair_capacity', tcslib.pair_capacity())
cs = tcslib.Charset()
print('codes %d  pair_of %d' % (len(cs.enc_single), len(cs.enc_pair)))
both = sorted(set(cs.enc_single) & set(cs.enc_pair))
print('in BOTH codes and pair_of: %d %r' % (len(both), both[:20]))
leadset = {}
for ch, (b1, b2) in cs.enc_pair.items():
    leadset.setdefault(b1, 0)
    leadset[b1] += 1
print('pair lead 分布:', dict(sorted(leadset.items())))
# 单字节 codes 的字节范围
bs = sorted(cs.enc_single.values())
print('codes bytes: %02X..%02X (%d)' % (bs[0], bs[-1], len(bs)))
print('codes 在 0xA1..0xAD 的:', ['%02X' % b for b in bs if 0xA1 <= b <= 0xAD])
# slot 与 pair 的关系: 是否 1175 个 pair 字都落在 slot 0..1174 之外有?
slots = sorted(tcslib.pair_slot(b1, b2) for b1, b2 in cs.enc_pair.values()
               if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI)
print('slots: %d..%d, 唯一 %d' % (slots[0], slots[-1], len(set(slots))))
print('hash check', tcslib.sha256_file(tcslib.CHARSET)[:16])
# encode_strict 存在?
print('has encode_strict', hasattr(cs, 'encode_strict'))
t = cs.encode_strict('何')
print('encode_strict(何) =', t.hex())
print('roundtrip', cs.decode(t)[0])
