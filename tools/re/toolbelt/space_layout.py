# -*- coding: utf-8 -*-
r"""space_layout.py -- 从 space_*.json 打印两个 IMG 的紧凑布局视图（只读）。"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))


def load(p):
    return json.load(open(p, encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                  'temp', 'r78'))
    a = ap.parse_args()
    menu = load(os.path.join(a.dir, 'space_menu.json'))
    gr = load(os.path.join(a.dir, 'space_gr.json'))

    for tag, r in (('MENU', menu), ('GR', gr)):
        print('===== %s (size 0x%X = %d) =====' % (tag, r['size'], r['size']))
        ents = sorted([e for e in r['entries']], key=lambda e: e['off'])
        # 但 entries 被裁剪过（只留有意义的） -> 用 gaps 的 prev/next 重建顺序不可靠
        print('  (entries 列表被裁剪, 仅 %d 条; 用 gaps 重建关键邻接)' % len(ents))
        print('  first_off=0x%X last_end=0x%X tail=%d' % (r['first_off'], r['last_end'],
                                                          r['size'] - r['last_end']))
        # 关键条目定位
        for nm in ('COMMON.PAK', 'FONT.RES', 'MENU.PAK', 'LOADING.PAK', 'LOAD_NEW_1.RSB',
                   'LOAD_NEW_2.RSB', 'EN_STRINGS.RES', 'EN_STRINGS.TXT', 'VIDEO.RSB',
                   'BNK_96_00.SS', 'GR.IMG'):
            for e in ents:
                if e['name'] == nm:
                    print('   %-18s idx=%-5d off=0x%09X stored=%-10d real=%-10d end=0x%09X '
                          'gap_to_next=%s(%s)' %
                          (nm, e['idx'], e['off'], e['stored'], e['real'], e['end'],
                           e['gap_to_next'], e['next_name']))
        # 围绕 COMMON.PAK 的邻接（用 gap 表）
        for g in r['gaps']:
            if g['prev'] in ('COMMON.PAK', 'FONT.RES', 'BNK_95_05.SS', 'CONTROLS.TXT'):
                print('   GAP after %-18s off=0x%09X len=%-9d zero=%-9d next=%s' %
                      (g['prev'], g['off'], g['len'], g['zero'], g['next']))
        print()


main()
