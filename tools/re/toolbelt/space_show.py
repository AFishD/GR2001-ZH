# -*- coding: utf-8 -*-
r"""space_show.py -- 查看 space_scan.py 的 JSON 结果（只读）。"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('--gaps', type=int, default=25)
    ap.add_argument('--ents', type=int, default=25)
    ap.add_argument('--minzero', type=int, default=0)
    a = ap.parse_args()
    r = json.load(open(a.json, encoding='utf-8'))
    print('=== %s (%s) ===' % (os.path.basename(a.json), r['target']))
    print('entries=%d live=%d first_off=0x%X last_end=0x%X size=0x%X' %
          (r['n_entries'], r['n_live'], r['first_off'], r['last_end'], r['size']))
    print('hdr=%s names_noff=0x%X names_nend=0x%X n_names=%d' %
          (r['hdr'], r['names_noff'], r['names_nend'], r['n_names']))
    t = r['totals']
    print('TOTALS gap=%d(z=%d) tail=%d(z=%d) dead=%d ent_tail0=%d stored-real=%d' % (
        t['gap_bytes'], t['gap_zero'], t['tail_bytes'], t['tail_zero'],
        t['dead_bytes'], t['ent_tail_zero'], t['stored_minus_real']))

    print('\n-- 头部/尾部 --')
    for h in r['head']:
        print('  HEAD off=0x%08X end=0x%08X len=%d zero=%d' % (h['off'], h['end'], h['len'], h['zero']))
    for h in r['tail']:
        print('  TAIL off=0x%08X end=0x%08X len=%d zero=%d' % (h['off'], h['end'], h['len'], h['zero']))

    gs = sorted(r['gaps'], key=lambda g: -g['len'])
    print('\n-- 最大 %d 个 gap --' % a.gaps)
    for g in gs[:a.gaps]:
        print('  off=0x%08X len=%-8d zero=%-8d  %-24s -> %s' %
              (g['off'], g['len'], g['zero'], g['prev'], g['next']))

    gz = sorted(r['gaps'], key=lambda g: -g['zero'])
    print('\n-- zero 最多的 %d 个 gap --' % a.gaps)
    for g in gz[:a.gaps]:
        if g['zero'] == 0:
            break
        print('  off=0x%08X len=%-8d zero=%-8d  %-24s -> %s' %
              (g['off'], g['len'], g['zero'], g['prev'], g['next']))

    es = sorted(r['entries'], key=lambda e: -(e['tail_zeros']))
    print('\n-- 尾部零最多的 %d 个条目 (tail_zeros>=%d) --' % (a.ents, a.minzero))
    for e in es[:a.ents]:
        if e['tail_zeros'] < a.minzero:
            break
        print('  #%-3d %-30s off=0x%08X stored=%-9d real=%-9d end0x%08X tail0=%-8d nz=%d nrun=%d' %
              (e['idx'], e['name'][:30], e['off'], e['stored'], e['real'], e['end'],
               e['tail_zeros'], e['nonzero_bytes'], e['n_zero_runs']))

    print('\n-- stored != real 的条目 --')
    n = 0
    for e in r['entries']:
        if e['stored'] != e['real']:
            n += 1
            if n <= 40:
                print('  #%-3d %-30s off=0x%08X stored=%-9d real=%-9d diff=%+d' %
                      (e['idx'], e['name'][:30], e['off'], e['stored'], e['real'],
                       e['stored'] - e['real']))
    print('  (共 %d 条)' % n)


main()
