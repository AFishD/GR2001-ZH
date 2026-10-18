# -*- coding: utf-8 -*-
"""r39: 深挖 SFXML:T0011 —— 表里的文本与盘上字节到底差在哪。只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T

iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))
cs = T.Charset()
e = iso.img_entry(T.MENU_LBA, T.XML_IDX)
blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
ents = dict((k, (o, ln, b)) for (k, o, ln, b) in T.parse_sfxml(blob))

for k in (11, 13):
    off, ln, old = ents[k]
    t, _ = cs.decode(old)
    back = cs.encode_strict(t)
    print('\n== T%04d  len=%d  old=%d B  back=%d B  back==old=%s ==' %
          (k, ln, len(old), len(back), back == old))
    print('   盘上 dec  : %r' % t)
    # 逐字符对照
    print('   逐字符 (盘上 dec):')
    for i, ch in enumerate(t[:24]):
        try:
            one = cs.encode_strict(ch)
        except T.CharsetError as ex:
            one = b'<ERR %s>' % str(ex)[:20].encode()
        print('      %2d  %r  U+%04X  -> %s' % (i, ch, ord(ch), one.hex(' ')))
    # 再看表里
    p = os.path.join(HERE, 'text_clean', 'GR_ZH92_text_long.csv')
    with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['id'] == 'SFXML:T%04d' % k:
                print('   表里 text_zh  : %r' % r['text_zh'][:60])
                print('   表里 text_edited: %r' % r['text_edited'][:60])
                print('   te == zh ? %s' % (r['text_edited'] == r['text_zh']))
                new = T.cell_to_bytes_text(r['text_edited'], cs, {})
                print('   te→bytes 前 24B: %s' % new[:24].hex(' '))
                print('   盘上原   前 24B: %s' % old[:24].hex(' '))
                # 逐字节比较
                for i in range(min(len(new), len(old))):
                    if new[i] != old[i]:
                        print('   首处不同 @%d: new=%02X old=%02X' % (i, new[i], old[i]))
                        print('     盘上 dec 周围: %r' % t[max(0, i - 4):i + 6])
                        break
                break
iso.close()
