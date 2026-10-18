# -*- coding: utf-8 -*-
"""r39 探针 6: 大 MEDIA 容器里到底有什么文本 + ELF 的去重分布。只读。"""
import collections
import os
import re
import struct
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

WORD = re.compile(r'[0-9A-Za-z]')
PUNCT = re.compile(r"[ \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
CJK = re.compile(r'[\u4e00-\u9fff]')
OKVIS = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}
STRUCT = ('XML', 'TXT', 'MIS', 'ATR', 'RES')


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
        return False, 'short', None
    if all(b in PRINTABLE for b in sb):
        t = sb.decode('ascii')
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.70:
            return False, 'ascii-word', None
    else:
        t = cs.decode(sb)[0]
        if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
            return False, 'pua', None
        if sum(1 for c in t if OKVIS.match(c)) / len(t) < 0.85:
            return False, 'visible', None
        if sum(1 for c in t if WORD.match(c)) / len(t) < 0.55:
            return False, 'cjk-word', None
        if not CJK.search(t):
            return False, 'no-cjk', None
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > 8:
        return False, 'char-repeat', None
    if len(t) >= 16 and not PUNCT.search(t):
        return False, 'no-punct', None
    if rep4(t):
        return False, 'repeat4', None
    return True, None, t


# 大 MEDIA 容器
print('=== 解压后最大的 12 个 MEDIA 容器 ===')
med = sorted([c for c in conts if c['kind'] == 'MEDIA'],
             key=lambda c: -c['stored'])[:12]
for c in med:
    b, _raw = FU.container_blob(iso, c)
    t0 = b[:4]
    print('\n-- %s  stored=%d  blob=%d  head=%s' %
          (c['name'], c['stored'], len(b), t0.hex(' ')))
    if t0 == b'PS2L':
        print('   PS2L 头 (PSS 视频流): 0x%02X' % b[4])
    kept = []
    seen = set()
    for m in idx.run_re(4).finditer(b):
        ok, r, t = judge(m.group(0), 'MEDIA')
        if ok and t not in seen:
            seen.add(t)
            kept.append(t)
    # 只显示"像人话"的: 含词边界空格且 >=2 个字母词
    good = [t for t in kept if re.search(r'[A-Za-z]{2,} [A-Za-z]{2,}', t)]
    print('   judge 保留不同串 %d; 其中"含两个以上单词" %d' % (len(kept), len(good)))
    for t in good[:14]:
        print('       GOOD %r' % t[:110])
    for t in kept[:10]:
        print('       raw  %r' % t[:90])

print('\n=== ELF: 全部保留串按长度分布 + 最长的 20 条 ===')
elf = [c for c in conts if c['kind'] == 'ELF'][0]
b, _raw = FU.container_blob(iso, elf)
kept, seen = [], set()
for m in idx.run_re(4).finditer(b):
    ok, r, t = judge(m.group(0), 'ELF')
    if ok and t not in seen:
        seen.add(t)
        kept.append(t)
print('distinct = %d' % len(kept))
hist = collections.Counter(len(t) // 10 * 10 for t in kept)
print('长度分布: %s' % dict(sorted(hist.items())))
good = [t for t in kept if re.search(r'[A-Za-z]{2,} [A-Za-z]{2,}', t)]
print('含两个以上单词的 = %d' % len(good))
for t in sorted(kept, key=len)[-20:]:
    print('   LONG %r' % t[:130])
iso.close()
