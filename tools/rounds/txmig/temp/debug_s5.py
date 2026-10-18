# -*- coding: utf-8 -*-
r"""debug_s5.py — 定位 [S5] 逐字符不一致的根因 (只读, 临时诊断)"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import migrate_legacy as M                                               # noqa: E402
import tcslib as T                                                       # noqa: E402

BASE, GATE = 0xB1, 0xBA
src = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
cs = T.Charset(T.CHARSET)
mp, extra = M.build_map(cs, BASE, GATE, {}, True, (GATE - T.LEAD_LO) * T.PAIR_STRIDE)
iso = T.Iso(src)
e = iso.img_entry(T.MENU_LBA, 25)
blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
iso.close()
cont = dict(name='LANG', tag='EN_STRINGS.RES@MENU', blob=blob)
ranges, used, info = M.payload_ranges(cont)
print('ranges=%d used=0x%X' % (len(ranges), used))

pair_of = {ch: tuple(p) for ch, p in cs.enc_pair.items()}
for _b, (ch, pair, _s) in mp.items():
    if pair is not None:
        pair_of.setdefault(ch, pair)
codes = dict(cs.codes)

for target in (0x125, 0x1FC, 0x206, 0x22F, 0x363):
    rng = next(((s, en) for (s, en) in ranges if s <= target < en), None)
    print('\n=== target 0x%X  payload=%s' % (target, rng))
    if rng is None:
        continue
    (s, en) = rng
    seg = blob[s:en]
    stat = {'per_code': {}, 'per_char': {}, 'n': 0}
    new, k = M.migrate_payload(seg, mp, BASE, GATE, stat)
    print('  seg len %d -> %d (migrated %d)' % (len(seg), len(new), k))
    lo, hi = max(0, target - s - 24), min(len(seg), target - s + 24)
    print('  old[%d:%d] = %s' % (lo, hi, seg[lo:hi].hex()))
    print('  new[%d:%d] = %s' % (lo, hi, new[lo:hi].hex()))
    t_old, mo = M.decode_with(seg, BASE, pair_of, codes)
    t_new, mn = M.decode_with(new, GATE, pair_of, codes)
    print('  t_old = %r' % t_old)
    print('  t_new = %r' % t_new)
    print('  map_old = %s' % [(i, b, c, l) for (i, l) in [(x, y) for (x, y) in mo]][:0] or '')
    print('  old 逐字节: %s' % ' '.join('%02X@%d+%d' % (seg[o], s + o, l) for (o, l) in mo))
