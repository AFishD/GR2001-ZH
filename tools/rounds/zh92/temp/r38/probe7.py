# -*- coding: utf-8 -*-
r"""probe7.py — 只看「与英文原盘不同」的容器: 它们各自贡献了什么证据

结论方向: 与英文盘**逐字节相同**的容器 ⇒ 命中必然是巧合 (可证明)。
           所以真正的证据只可能来自**不同的**那几个容器。
本脚本量化: 每个不同的容器在各阈值下贡献多少字, 以及据此的可回收量。
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import font_usage as F  # noqa: E402
import tcslib as T     # noqa: E402

TH = (4, 8, 16, 24, 32, 48)
ZH = os.path.join(REPO, 'work/builds/GR_ZH92/GR_ZH92.iso')
EN = os.path.join(REPO, 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso')
idx = F.CharsetIndex()


def hits(blob, t):
    out = set()
    for m in idx.run_re(4).finditer(blob):
        L = m.end() - m.start()
        if L < t:
            continue
        for ch in idx.decode_chars(m.group(0)):
            out.add(ch)
    return out


izh, ien = T.Iso(ZH), T.Iso(EN)
czh = F.build_container_list(izh)
cen = F.build_container_list(ien)
key = lambda c: (c['img'], c['idx'], c['name'])
men = {key(c): c for c in cen}
print('容器: zh=%d en=%d' % (len(czh), len(cen)))
t0 = time.time()
rows = []
for c in czh:
    o = men.get(key(c))
    if o is None or o['stored'] != c['stored']:
        rows.append((c, o, 'size/name'))
        continue
    if F.container_sha1(izh, c) != F.container_sha1(ien, o):
        rows.append((c, o, 'bytes'))
print('不同的容器 %d 个 (%.1fs)\n' % (len(rows), time.time() - t0))

print('%-9s %-6s %-24s %-9s %8s | %s' %
      ('img', 'idx', 'name', 'kind', 'bytes', ' '.join('%6d' % t for t in TH)))
detail = {}
union = {t: set() for t in TH}
for c, o, why in sorted(rows, key=lambda r: (r[0]['img'], r[0]['idx'])):
    bz, _ = F.container_blob(izh, c)
    be, _ = F.container_blob(ien, o) if o else (b'', b'')
    hz = {t: hits(bz, t) for t in TH}
    he = {t: hits(be, t) for t in TH}
    detail['%s#%s' % (c['img'], c['idx'])] = dict(
        name=c['name'], kind=c['kind'], blob=len(bz), why=why,
        hz={str(t): sorted(hz[t]) for t in TH},
        he={str(t): sorted(he[t]) for t in TH},
        new={str(t): sorted(hz[t] - he[t]) for t in TH})
    for t in TH:
        union[t] |= hz[t]
    print('%-9s %-6s %-24s %-9s %8d | %s   (对照侧: %s)'
          % (c['img'], c['idx'], c['name'][:24], c['kind'], len(bz),
             ' '.join('%6d' % len(hz[t]) for t in TH),
             ' '.join('%d' % len(he[t]) for t in TH)))

font = set(idx.chars)
print('\n【只算"与英文盘不同的容器"的并集】')
for t in TH:
    n = len(union[t] & font)
    print('  run>=%-3d: 命中字 %4d (字库内 %4d) ⇒ 可回收 %4d 字'
          % (t, len(union[t]), n, len(font) - n))

# 只算 LANG + SFXML
print('\n【只算 LANG + SFXML (现有覆盖)】')
for t in TH:
    u = set()
    for c, o, why in rows:
        if c['kind'] in ('LANG', 'SFXML'):
            bz, _ = F.container_blob(izh, c)
            u |= hits(bz, t)
    n = len(u & font)
    print('  run>=%-3d: 命中字 %4d (字库内 %4d) ⇒ 可回收 %4d 字'
          % (t, len(u), n, len(font) - n))

# 只算 文本类 kind (LANG/SFXML/XML/TXT/MIS/ATR/RES/ELF)
print('\n【文本类 kind: LANG/SFXML/XML/TXT/MIS/ATR/RES/ELF】')
TXTK = ('LANG', 'SFXML', 'XML', 'TXT', 'MIS', 'ATR', 'RES', 'ELF')
for t in TH:
    u = set()
    for c, o, why in rows:
        if c['kind'] in TXTK:
            bz, _ = F.container_blob(izh, c)
            u |= hits(bz, t)
    n = len(u & font)
    print('  run>=%-3d: 命中字 %4d (字库内 %4d) ⇒ 可回收 %4d 字'
          % (t, len(u), n, len(font) - n))

json.dump(detail, open(os.path.join(REPO, 'work/builds/GR_ZH92/temp/r38/diffcontainers.json'),
                       'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n-> diffcontainers.json')
izh.close()
ien.close()
