# -*- coding: utf-8 -*-
r"""space_orphan.py -- 判定"孤儿区"到底是哪个条目的旧副本（只读）。

原理: 对每个 >=2KB 的 gap，在**全部条目**里找 stored 相近且内容逐字节相同的条目
      （先比 4KB 头，再整段 md5）⇒ 命中即证明该 gap 是"某文件的旧位置"，是可回收垃圾。
"""
import argparse
import hashlib
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
LBA = {'menu': 776286, 'gr': 19175}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='gr', choices=['gr', 'menu'])
    ap.add_argument('--json', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    lba = LBA[a.target]
    r = json.load(open(a.json, encoding='utf-8'))
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)

    # 头 4KB 哈希表 (只对 stored>=2048 的条目)
    tbl = {}
    for e in ents:
        if e['stored'] >= 2048 and e['off'] > 0:
            h = hashlib.md5(iso.read(lba * SEC + e['off'], 4096)).hexdigest()
            tbl.setdefault(h, []).append(e)

    gaps = sorted(r['gaps'], key=lambda g: -g['len'])
    res = []
    for g in gaps:
        if g['len'] < 2048:
            continue
        head = iso.read(lba * SEC + g['off'], min(4096, g['len']))
        h = hashlib.md5(head).hexdigest()
        cand = tbl.get(h, [])
        d = dict(off=g['off'], len=g['len'], zero=g['zero'],
                 prev=g['prev'], next=g['next'], match=None)
        for e in cand:
            if e['stored'] <= g['len']:
                # 整段比
                n = e['stored']
                b1 = iso.read(lba * SEC + g['off'], n)
                b2 = iso.read(lba * SEC + e['off'], n)
                if b1 == b2:
                    d['match'] = dict(name=e['name'], idx=e['idx'], off=e['off'],
                                      stored=e['stored'], exact=True)
                    break
                d['match'] = dict(name=e['name'], idx=e['idx'], off=e['off'],
                                  stored=e['stored'], exact=False)
            else:
                # 条目比 gap 大: 看 gap 是不是条目的前缀
                n = g['len']
                if iso.read(lba * SEC + g['off'], n) == iso.read(lba * SEC + e['off'], n):
                    d['match'] = dict(name=e['name'], idx=e['idx'], off=e['off'],
                                      stored=e['stored'], exact=False, prefix=True)
                    break
        res.append(d)
    iso.close()
    tot = sum(x['len'] for x in res)
    tot_orph = sum(x['len'] for x in res if x['match'])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dict(target=a.target, gaps=res, total=tot, orphan=tot_orph),
              open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('== %s: >=2KB gap %d 个, 合计 %d B; 其中能对上旧副本的 %d B ==' %
          (a.target, len(res), tot, tot_orph))
    for x in res:
        m = x['match']
        print('  0x%09X len=%-9d z=%-7d -> %-32s %s' %
              (x['off'], x['len'], x['zero'],
               (('%s (idx=%d off=0x%X stored=%d)' % (m['name'], m['idx'], m['off'],
                                                     m['stored'])) if m else '(未匹配)'),
               ('EXACT' if m and m.get('exact') else ('PREFIX' if m else ''))))
    print('-> %s' % a.out)


main()
