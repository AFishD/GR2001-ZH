# -*- coding: utf-8 -*-
r"""space_gap.py -- GR.IMG / MENU.IMG 空隙的性质判定（只读）。

三个判据，逐个 gap 判"能不能用"：
  Z  全零率           zero/len
  O  孤儿重复         内容与某个存活条目的开头 64KB 相同 (或整段哈希命中) ⇒ 原文件被去重/删表遗留
  E  贴边             紧贴前一条目或后一条目 ⇒ 可能是对齐填充/条目 over-declare

另列 **高零率条目**（stored 区 >=90% 全零）= 死条目候选。

用法: python tools/re/toolbelt/space_gap.py --json <space_gr.json> --target gr --out <out.json>
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


def md5(b):
    return hashlib.md5(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--json', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--top', type=int, default=40)
    a = ap.parse_args()
    r = json.load(open(a.json, encoding='utf-8'))
    base = r['base']
    iso = tcslib.Iso(a.iso)

    # 存活条目哈希 (前 64KB)
    ent_hash = {}
    lba = r['lba']
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    live = [e for e in ents if 0 < e['off'] < r['size'] and e['stored'] > 0]
    byoff = sorted(live, key=lambda e: e['off'])
    for e in byoff:
        head = iso.read(base + e['off'], min(65536, e['stored']))
        ent_hash.setdefault(md5(head), []).append(e['name'])

    print('== %s: %d 条目, 建立 %d 个 64KB 头哈希 ==' % (r['target'], len(ents), len(ent_hash)))

    gaps = sorted(r['gaps'], key=lambda g: -g['len'])
    out = []
    for g in gaps:
        if g['len'] < 2048:
            continue
        head = iso.read(base + g['off'], min(65536, g['len']))
        h = md5(head)
        match = ent_hash.get(h)
        d = dict(off=g['off'], len=g['len'], zero=g['zero'],
                 zfrac=round(g['zero'] / g['len'], 4),
                 prev=g['prev'], next=g['next'], head_md5=h, dup_of=match)
        out.append(d)

    iso.close()

    # 高零率条目: 用 space_scan 的 entries（只含 stored!=real 或 tail0>=1024）
    zeroent = sorted([e for e in r['entries'] if e['stored'] > 0 and
                      e['all_zero_bytes'] / e['stored'] >= 0.90],
                     key=lambda e: -e['stored'])

    rep = dict(target=r['target'], size=r['size'],
               gaps_big=out, zero_heavy_entries=zeroent,
               totals=dict(
                   gap_big=sum(g['len'] for g in out),
                   gap_big_zero=sum(g['zero'] for g in out),
                   gap_big_orzero=sum(g['len'] for g in out if g['zfrac'] >= 0.999),
                   gap_big_dup=sum(g['len'] for g in out if g['dup_of']),
                   zeroent_bytes=sum(e['stored'] for e in zeroent),
                   zeroent_zero=sum(e['all_zero_bytes'] for e in zeroent),
               ))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)

    print('\n-- >=2KB 空隙 (%d 个)，按大小排序，标出全零/孤儿重复 --' % len(out))
    for d in out[:a.top]:
        print('  0x%09X len=%-9d z=%-8d(%.3f) dup=%-28s %s -> %s'
              % (d['off'], d['len'], d['zero'], d['zfrac'],
                 (d['dup_of'][0][:28] if d['dup_of'] else '-'), d['prev'], d['next']))
    print('\n-- 高零率条目 (>=90%% 零) --')
    for e in zeroent[:30]:
        print('  #%-4d %-28s off=0x%09X stored=%-9d zero=%-9d (%.3f) nz=%d'
              % (e['idx'], e['name'][:28], e['off'], e['stored'], e['all_zero_bytes'],
                 e['all_zero_bytes'] / e['stored'], e['nonzero_bytes']))
    print('\n-- 汇合 --')
    for k, v in rep['totals'].items():
        print('  %-18s %d' % (k, v))
    print('-> %s' % a.out)


main()
