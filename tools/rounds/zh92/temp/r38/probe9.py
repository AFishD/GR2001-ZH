# -*- coding: utf-8 -*-
r"""probe9.py — 151 个闲置字按"码位类型"分解: 到底能腾出几个**合法对偶格位**?"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
import font_usage as F  # noqa: E402

idx = F.CharsetIndex()
J = json.load(open(os.path.join(REPO, 'work/builds/GR_ZH92/temp/r38/字库用量核算.json'),
                   encoding='utf-8')) if os.path.isfile(
    os.path.join(REPO, 'work/builds/GR_ZH92/temp/r38/字库用量核算.json')) else None
e0 = set(J['evidence']['e0']) if J else None
if e0 is None:
    print('!! 还没有 JSON 报告, 用 CSV 口径算')
    import tcslib as T
    rows, files, notes = F.read_text_tables(os.path.join(REPO, 'work/builds/GR_ZH92/text'))
    cur = set()
    for r in rows:
        cur |= r['cur']
    e0 = cur

idle = sorted(set(idx.chars) - e0)
used = sorted(set(idx.chars) & e0)
print('字库 %d 字: 用到 %d / 闲置 %d' % (len(idx.chars), len(used), len(idle)))


def cls(ch):
    if ch in idx.enc_single:
        return 'single(单字节码)'
    p = idx.enc_pair.get(ch)
    if not p:
        return '??'
    return 'legal_pair(合法对偶)' if F.LEGAL_LEAD_LO <= p[0] < F.LEGAL_LEAD_HI \
        else 'dead_pair(死对偶 lead>=0xAE)'


buckets = {}
for ch in idle:
    buckets.setdefault(cls(ch), []).append(ch)
print('\n【闲置 %d 个】按码位类型:' % len(idle))
for k in sorted(buckets, key=lambda x: -len(buckets[x])):
    v = buckets[k]
    print('   %-28s %4d 个: %s' % (k, len(v), ''.join(v[:70]) + ('…' if len(v) > 70 else '')))

buckets_u = {}
for ch in used:
    buckets_u.setdefault(cls(ch), []).append(ch)
print('\n【用到 %d 个】按码位类型:' % len(used))
for k in sorted(buckets_u, key=lambda x: -len(buckets_u[x])):
    print('   %-28s %4d 个' % (k, len(buckets_u[k])))

print('\n【闲置里的合法对偶字 (能腾出图集格位的就是这些)】')
lp = buckets.get('legal_pair(合法对偶)', [])
for ch in lp:
    p = idx.enc_pair[ch]
    slot = F.pair_slot(p)
    x, y = F.slot_cell(slot)
    print('   %s  U+%04X  码 %02X%02X  slot=%d 图集(%d,%d)' % (ch, ord(ch), p[0], p[1],
                                                              slot, x, y))
print('   ⇒ 共 %d 个 ⇒ 回收能腾出 %d 个合法对偶格位' % (len(lp), len(lp)))

print('\n【核对 Lead 报告里点名的人名用字】')
for ch in '乔亨伟伯兰冈凡刘丁丹丽佐俊傅勃卜':
    if ch not in idx.chars:
        print('   %s 不在字库' % ch)
        continue
    p = idx.enc_pair.get(ch)
    s = ('%02X%02X' % p) if p else ('单字节 %02X' % idx.enc_single[ch])
    print('   %s  %-10s %-28s %s' % (ch, s, cls(ch), '闲置' if ch in set(idle) else '在用'))

cap = idx.pair_capacity()
print('\n【容量】合法对偶空间 %d, 已用 %d, 空位 %d' % (cap['total'], cap['used'], cap['free']))
print('  回收腾出 %d ⇒ 可用 %d; 要补 70 ⇒ 余 %d'
      % (len(lp), cap['free'] + len(lp), cap['free'] + len(lp) - 70))
print('  (若把 137 个死 pair 也算成"可回收", 得到 78+%d=%d 的数字 —— 但死 pair 的 lead>=0xAE,'
      % (len(idle), cap['free'] + len(idle)))
print('   引擎 sltiu lead,0xAE 根本不认, 它们**不占**合法对偶空间, 释放它们换不来新字格位。)')
