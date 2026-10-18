# -*- coding: utf-8 -*-
r"""v3_diag.py — 诊断: 新盘上 的/你 到底是怎么编码的? 和用户 CSV 的原文对不对得上?
"""
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

cs = tcslib.Charset()
print('新 charset: 的=%s 你=%s 虽=%s' % (cs.enc_pair.get('的'), cs.enc_pair.get('你'),
                                        cs.enc_pair.get('虽')))
print('单字节码里是否还有 0xAF/0xB0: %s / %s' % (cs.codes.get(0xAF), cs.codes.get(0xB0)))

# 用户 CSV 原文
csv_txt = {}
for fn in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text'))):
    if fn.endswith('.csv'):
        with open(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text', fn),
                  encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                t = r.get('text_edited')
                if t:
                    csv_txt[r['id']] = t
print('CSV 条目 %d' % len(csv_txt))

for tag, path in (('新盘 GR_ZH93', 'work/builds/GR_ZH93/GR_ZH93.iso'),
                  ('现役盘 GR_ZH92', 'work/builds/GR_ZH92/GR_ZH92.iso')):
    iso = tcslib.Iso(os.path.join(REPO, path))
    e = iso.img_entry(tcslib.MENU_LBA, 25)
    blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    iso.close()
    ents, _ = tcslib.parse_lang(blob)
    print()
    print('== %s ==' % tag)
    for e2 in ents:
        rid = 'G%03d.I%03d' % (e2.g, e2.i)
        if rid not in ('G007.I006', 'G058.I797'):
            continue
        want = csv_txt.get(rid, '')
        got, _ = cs.decode(e2.data)
        print('  %s' % rid)
        print('     CSV 原文 : %s' % want.replace('\n', '\\n')[:90])
        print('     盘上解码 : %s' % got.replace('\n', '\\n')[:90])
        print('     一致? %s' % ('✓' if got == tcslib.text_to_cell(want) else '✗'))
        print('     前 40 字节: %s' % e2.data[:40].hex(' '))
        print('     含 0xAF: %d 次, 含 A8BA: %d 次' % (e2.data.count(0xAF),
                                                       e2.data.count(bytes.fromhex('a8ba'))))
