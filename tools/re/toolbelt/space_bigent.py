# -*- coding: utf-8 -*-
r"""space_bigent.py -- 列出 IMG 里的大条目 + 搜索某段文本的归属（只读）。"""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='gr', choices=['gr', 'menu'])
    ap.add_argument('--min', type=int, default=500000)
    ap.add_argument('--needle', default='// weapons and items')
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    lba = LBA[a.target]
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    live = sorted([e for e in ents if e['off'] > 0], key=lambda e: -e['stored'])
    print('== %s: 条目 %d，stored>=%d 的 %d 条 ==' %
          (a.target, len(ents), a.min, sum(1 for e in live if e['stored'] >= a.min)))
    for e in live:
        if e['stored'] < a.min:
            break
        print('   #%-5d %-34s off=0x%09X stored=%-10d real=%-10d' %
              (e['idx'], e['name'][:34], e['off'], e['stored'], e['real']))
    # needle 搜索: 在条目数据里找
    nb = a.needle.encode('ascii')
    print('\n== 搜 needle %r ==' % a.needle)
    hits = []
    for e in ents:
        if e['off'] <= 0 or e['stored'] <= 0:
            continue
        d = iso.read(lba * SEC + e['off'], min(e['stored'], 1 << 20))
        if nb in d:
            hits.append((e['name'], e['idx'], e['off'], e['stored'], d.find(nb)))
    for h in hits:
        print('   %-34s idx=%-5d off=0x%09X stored=%-10d at=+0x%X' % h)
    if not hits:
        print('   (无命中)')
    iso.close()


main()
