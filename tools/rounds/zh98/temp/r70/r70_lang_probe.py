# -*- coding: utf-8 -*-
r"""r70_lang_probe.py — 屏幕上的武器说明到底来自 SFXML 还是语言表(LANG)?

线索: GR_ZH114 盘上 SFXML 里 T0010 写的是
        「起爆时破片以扇形射出 … 杀伤区 … 毁伤区」
      而实拍屏幕上写的是
        「当引爆时，可以崩放出 … 杀害区」
      ⇒ 若语言表里能搜到后者, 说明**两处都存了同一段说明**, 我们只改了 SFXML。
"""
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

c = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                   'charset_compiled_zh16.json'), encoding='utf-8'))
pair = {(a, b): ch for ch, (a, b) in c['pair_of'].items()}
sing = {v: ch for ch, v in c['codes'].items()}
sing_rev = {ch: v for v, ch in sing.items()}


def dec(b):
    o, i = [], 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            o.append(chr(x)); i += 1
        elif x in sing:
            o.append(sing[x]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in pair:
            o.append(pair[(b[i], b[i + 1])]); i += 2
        else:
            o.append('\ufffd'); i += 1
    return ''.join(o)


def enc(s):
    o = bytearray()
    for ch in s:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in c['pair_of']:
            o += bytes(c['pair_of'][ch])
        elif ch in sing_rev:
            o.append(sing_rev[ch])
        else:
            return None
    return bytes(o)


# LANG 两份副本
copies = tcslib.RES['LANG']['copies']
print('LANG 副本: %s' % [(x[0], x[2]) for x in copies])

needles = ['当引爆时', '可以崩放出', '杀害区', '毁伤区', '起爆时破片以扇形射出',
           '定向反步兵地雷', '出于装药']
for spec in copies:
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'GR_ZH114.iso'))
    e = iso.img_entry(spec[1], spec[2])
    st = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(st))
    print()
    print('=== %s#%d %s (blob %d B) ===' % (spec[0], spec[2], spec[3], len(blob)))
    for s in needles:
        b = enc(s)
        if b is None:
            print('   %-22s (charset 外)' % s); continue
        n = blob.count(b)
        print('   %-22s 出现 %d 次' % (s, n))
    # 直接解出含 "M18" 或 "定向反步兵" 的条目
    txt = dec(blob)
    for kw in ('定向反步兵地雷', '当引爆时'):
        i = txt.find(kw)
        if i >= 0:
            print('   ★ 含「%s」的上下文: …%s…' % (kw, re.sub(r'\s+', '／', txt[max(0, i - 60):i + 120])))
            break
