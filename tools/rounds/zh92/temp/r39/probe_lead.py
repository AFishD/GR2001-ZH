# -*- coding: utf-8 -*-
"""r39: 当前字符集的 lead 字节直方图 + 哪些字能编码出 0xAF/0xB0 单字节。只读。"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T

cs = T.Charset()
print('LEAD_LO/HI = 0x%02X/0x%02X   PAIR_LEAD_LO/HI = 0x%02X/0x%02X'
      % (T.LEAD_LO, T.LEAD_HI, T.PAIR_LEAD_LO, T.PAIR_LEAD_HI))
hist = collections.Counter(p[0] for p in cs.pair_of)
print('对偶 lead 直方图: %s' % ' '.join('%02X:%d' % (k, hist[k]) for k in sorted(hist)))
s1 = {v: ch for ch, v in cs.enc_single.items()}
print('单字节码数量 %d; 0xA1..0xB0 里的单字节码: %s'
      % (len(cs.enc_single),
         ' '.join('%02X=%s' % (b, s1[b]) for b in sorted(s1) if 0xA1 <= b <= 0xB0) or '(无)'))
# 哪些字会编码出 0xAF/0xB0 单字节
for b in (0xAF, 0xB0):
    ch = s1.get(b)
    print(' 单字节 0x%02X -> %r' % (b, ch))
# 盘上到底有没有裸 0xAF?
iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))
e = iso.img_entry(T.MENU_LBA, T.XML_IDX)
blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
ents = [(k, o, ln, b) for (k, o, ln, b) in T.parse_sfxml(blob)]
n_af = sum(b.count(0xAF) for (_k, _o, _l, b) in ents)
n_b0 = sum(b.count(0xB0) for (_k, _o, _l, b) in ents)
print('\nSFXML 正文里裸字节: 0xAF × %d, 0xB0 × %d' % (n_af, n_b0))
for (k, _o, _l, bb) in ents:
    if 0xAF in bb or 0xB0 in bb:
        i = bb.find(0xAF) if 0xAF in bb else bb.find(0xB0)
        print('   T%04d: 0x%02X @%d  上下文 %s' % (k, bb[i], i, bb[max(0, i - 3):i + 4].hex(' ')))
        if k > 40:
            break
# LANG 侧
e2 = iso.img_entry(T.MENU_LBA, T.LANG_MENU_IDX)
blob2 = b''.join(s[0] for s in T.lzo_subs(iso.read(e2['iso_off'], e2['stored'])))
le, _ = T.parse_lang(blob2)
naf = sum(x.data.count(0xAF) for x in le)
nb0 = sum(x.data.count(0xB0) for x in le)
print('\nLANG 正文里裸字节: 0xAF × %d, 0xB0 × %d' % (naf, nb0))
print('\nCharset JSON 顶层标记:')
raw = json.load(io.open(T.CHARSET, encoding='utf-8'))
for k in ('_font_ext_planc_zh93', '_font_ext_zh93_fix'):
    print('   %s = %s' % (k, json.dumps(raw.get(k), ensure_ascii=False)[:200]))
iso.close()
