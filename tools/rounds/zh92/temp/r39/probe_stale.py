# -*- coding: utf-8 -*-
"""r39: 为什么 text_clean 注入会「改 29 条」而 stale 判据没拦住? 逐条查。只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CSVD = os.path.join(HERE, 'text_clean')
iso = T.Iso(ISO)
cs = T.Charset()
e = iso.img_entry(T.MENU_LBA, T.XML_IDX)
raw = iso.read(e['iso_off'], e['stored'])
blob = b''.join(s[0] for s in T.lzo_subs(raw))
ents = dict((k, (o, ln, b)) for (k, o, ln, b) in T.parse_sfxml(blob))

n_stale = n_changed = 0
for fn in sorted(os.listdir(CSVD)):
    if not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(CSVD, fn), 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            te = r['text_edited']
            if te.strip() == '' or te == r['text_zh']:
                continue
            if r['resource'] != 'SFXML':
                continue
            loc = r['entry_index']
            k = int(loc[1:])
            off, ln, old = ents[k]
            t_old, _ = cs.decode(old)
            try:
                back = cs.encode_strict(t_old)
            except T.CharsetError as ex:
                back = None
                why = str(ex)[:60]
            stale = (back != old)
            try:
                new = T.cell_to_bytes_text(te, cs, {})
            except Exception as ex:                                  # noqa: BLE001
                new = None
                print('  %s  cell_to_bytes_text 抛错: %s' % (r['id'], ex))
                continue
            if stale:
                n_stale += 1
            if new != old:
                n_changed += 1
                print('  %s (%s): stale=%s  new==old=%s' % (r['id'], loc, stale, new == old))
                print('     盘上 dec : %r' % (t_old[:40],))
                print('     back==old : %s' % (back == old,))
                print('     表里 zh  : %r' % (r['text_zh'][:40],))
                print('     te==zh    : %s' % (te == r['text_zh'],))
                print('     新编码前20B: %s' % new[:20].hex(' '))
                print('     盘上原前20B: %s' % old[:20].hex(' '))
                if n_changed >= 3:
                    break
    if n_changed >= 3:
        break
print('\nstale=%d  changed=%d' % (n_stale, n_changed))
iso.close()
