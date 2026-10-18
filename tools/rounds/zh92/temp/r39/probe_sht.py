# -*- coding: utf-8 -*-
"""r39 探针 8: .SHT(归 MEDIA) 与 RSB/OTHER 高分容器里到底是什么文本 —— 定阈值。只读。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ZH)
cs = T.Charset()
idx = FU.CharsetIndex()
conts = FU.build_container_list(iso)
by = {}
for c in conts:
    by.setdefault(c['name'], c)

WORD = re.compile(r'[0-9A-Za-z]')
PUNCT = re.compile(r"[ \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
CJK = re.compile(r'[\u4e00-\u9fff]')
OKVIS = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}
STRUCT = ('XML', 'TXT', 'MIS', 'ATR', 'RES')
WORDSPACE = re.compile(r'[0-9A-Za-z][ \t][0-9A-Za-z]')
CJK2 = re.compile(r'[\u4e00-\u9fff]{2,}')


def rep4(t):
    if len(t) < 8:
        return False
    seen = set()
    for i in range(len(t) - 3):
        s = t[i:i + 4]
        if s in seen:
            return True
        seen.add(s)
    return False


def judge(sb, kind):
    mr = 6 if kind in STRUCT else 12
    if len(sb) < mr:
        return False, None
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.70:
            return False, None
    else:
        t = cs.decode(sb)[0]
        if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
            return False, None
        if sum(1 for c in t if OKVIS.match(c)) / len(t) < 0.85:
            return False, None
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.55:
            return False, None
        if not CJK.search(t):
            return False, None
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > 8:
        return False, None
    if len(t) >= 16 and not PUNCT.search(t):
        return False, None
    if rep4(t):
        return False, None
    if kind not in STRUCT and not (WORDSPACE.search(t) or CJK2.search(t)):
        return False, None
    return True, t


def dump(name, kind=None, limit=40, label=''):
    c = by[name]
    b, _raw = FU.container_blob(iso, c)
    k = kind or c['kind']
    sb = []
    for m in idx.run_re(4).finditer(b):
        ok, t = judge(m.group(0), k)
        if ok:
            sb.append(t)
    seen = []
    s = set()
    for t in sb:
        if t not in s:
            s.add(t)
            seen.append(t)
    wsw = [t for t in seen if WORDSPACE.search(t)]
    print('\n== %s (%s) blob=%d  保留 %d 行 / 去重 %d; 其中"词 空格 词" %d =='
          % (name, k, len(b), len(sb), len(seen), len(wsw)))
    for t in wsw[:limit]:
        print('   W  %r' % t[:120])
    for t in [x for x in seen if x not in wsw][:max(0, limit - len(wsw[:limit]))]:
        print('   -  %r' % t[:120])


for nm in ('D01_BEACH.SHT', 'D06_GHOSTTOWN.SHT', 'MUSIC.TM'):
    dump(nm)
for nm in ('MP04_VALLEY.BMZ', 'M11_POW_CAMP.BMZ', 'MAIN_MENU_PS2.RSB'):
    dump(nm)
for nm in ('EXPORT_PREPARE.CONFIG', 'IKE.SDF', 'NO_RESTRICTIONS.KIL', 'D01_BEACH.AOL'):
    dump(nm)
for nm in ('EN_STRINGS.RES', 'FONT.RES', 'IKE.RES'):
    dump(nm, limit=20)
iso.close()
