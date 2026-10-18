# -*- coding: utf-8 -*-
r"""space_growplan.py -- 设计 "COMMON.PAK 原地长大 N 字节" 的最小搬迁方案（只读，只算）。

输出:
  1. COMMON.PAK 之后按 off 排序的条目链，累计到 N 字节需要搬走哪几条；
  2. MENU.IMG / GR.IMG 里可用的空位清单（全零尾 + 全零 gap），能装下多少；
  3. 一个可行的落点分配（16 字节对齐）。
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
LBA = {'menu': 776286, 'gr': 19175}
SIZES = {'menu': 58300882, 'gr': 1550563328}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='menu', choices=['menu', 'gr'])
    ap.add_argument('--need', type=int, nargs='+', default=[32768, 40960, 41440, 66016])
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r78', 'growplan.json'))
    a = ap.parse_args()
    lba, size = LBA[a.target], SIZES[a.target]
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    live = sorted([e for e in ents if 0 < e['off'] < size and e['stored'] > 0],
                  key=lambda e: e['off'])
    pak = next(e for e in live if e['name'] == 'COMMON.PAK')
    pak_end = pak['off'] + pak['stored']
    print('== %s: COMMON.PAK off=0x%X stored=%d end=0x%X 容器=%d ==' %
          (a.target, pak['off'], pak['stored'], pak_end, size))
    k = live.index(pak)
    print('\n-- COMMON.PAK 之后的条目链 --')
    acc, chain = 0, []
    for e in live[k + 1:]:
        acc += e['off'] - (pak_end + acc) if False else 0
        chain.append(e)
    # 正确口径: 要腾出 [pak_end, pak_end+N) -> 搬走所有 off 落在该区间的条目
    for N in a.need:
        hi = pak_end + N
        vic = [e for e in live if pak_end <= e['off'] < hi or
               (e['off'] < pak_end and e['off'] + e['stored'] > pak_end)]
        tot = sum(e['stored'] for e in vic)
        print('\n  N=%-7d 区间 [0x%X,0x%X): 需搬走 %d 条, 合计 stored=%d' %
              (N, pak_end, hi, len(vic), tot))
        for e in vic:
            print('     #%-5d %-28s off=0x%09X stored=%-9d real=%-9d end=0x%09X' %
                  (e['idx'], e['name'][:28], e['off'], e['stored'], e['real'],
                   e['off'] + e['stored']))

    # 可用空位: 全零尾 + 全零 gap（用 space_*.json）
    d = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r78',
                     'space_%s.json' % a.target)
    r = json.load(open(d, encoding='utf-8'))
    slots = []
    for t in r['tail']:
        slots.append(dict(off=t['off'], end=t['end'], len=t['len'], zero=t['zero'],
                          kind='tail', prev='(容器尾)', next=None))
    for g in r['gaps']:
        if g['zero'] == g['len'] and g['len'] >= 256:
            slots.append(dict(off=g['off'], end=g['end'], len=g['len'], zero=g['zero'],
                              kind='zero-gap', prev=g['prev'], next=g['next']))
    slots.sort(key=lambda s: -s['len'])
    print('\n-- 可落点（全零, >=256B）：%d 处, 合计 %d B --' % (len(slots),
                                                              sum(s['len'] for s in slots)))
    for s in slots[:24]:
        print('     %-9s off=0x%09X len=%-9d zero=%-9d  %s -> %s' %
              (s['kind'], s['off'], s['len'], s['zero'], s['prev'], s['next']))
    print('     合计 = %d B' % sum(s['len'] for s in slots))
    # 现役 PAK 身后余量
    print('\n  现役 COMMON.PAK 身后余量 = %d B (下一条 %s @0x%X)' %
          (live[k + 1]['off'] - pak_end, live[k + 1]['name'], live[k + 1]['off']))
    iso.close()
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    json.dump(dict(target=a.target, pak=dict(off=pak['off'], stored=pak['stored'],
                                             end=pak_end), slots=slots,
                   nextent=dict(name=live[k + 1]['name'], off=live[k + 1]['off'])),
              open(a.json, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


main()
