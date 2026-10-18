# -*- coding: utf-8 -*-
r"""r58 探针10: 生成"迁移清单"要用的证据哈希 (只读)。

对**每个匹配登记表模式的容器**算:
  slot_sha256        = 盘上槽位原始字节的 sha256 (内容寻址)
  stale_text_sha256  = 陈旧码表(G0)解出的文本 sha256
  cur_text_sha256    = 现役码表(G2)解出的文本 sha256
  stale_changed      = 陈旧→现役 整块逐字重映射会改多少字节
  cur_changed        = 现役→现役 (恒 0, 作为"已经在现役码表上"的对照)
"""
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

G0P = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
G1P = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
G2P = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
G0, G1, G2 = (tcslib.Charset(p) for p in (G0P, G1P, G2P))
PAT = (r'^(?:EN|DE|ES|FR|IT)_STRINGS\.RES$', r'^(?:EN|DE|ES|FR|IT)_STRINGS\.TXT$',
       r'^(?:EN|DE|ES|FR|IT)_SPECIAL_FEATURE\.XML$', r'^IGORHELP\.TXT$')
H = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


def remap_changed(blob, src, dst):
    text, mp = src.decode(blob)
    n = len(blob)
    chg = 0
    nfail = nlen = 0
    for i, ch in enumerate(text):
        a = mp[i]
        b = mp[i + 1] if i + 1 < len(text) else n
        try:
            nb = dst.encode_strict(ch)
        except tcslib.CharsetError:
            nfail += 1
            continue
        if len(nb) != b - a:
            nlen += 1
            continue
        if nb != blob[a:b]:
            chg += len(nb)
    return chg, nfail, nlen


iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso'))
rows = []
for (tag, lba, idx, e) in FC.enumerate_containers(iso):
    if not any(re.match(p, e['name']) for p in PAT):
        continue
    s = FC.Slot(iso, tag, lba, idx)
    t0, t1, t2 = (c.decode(s.blob)[0] for c in (G0, G1, G2))
    c0 = remap_changed(s.blob, G0, G2)
    c1 = remap_changed(s.blob, G1, G2)
    rows.append(dict(key='%s#%d %s' % (tag, idx, e['name']), name=e['name'],
                     blob=len(s.blob), slot=s.slot,
                     slot_sha=hashlib.sha256(s.raw).hexdigest(),
                     s0=H(t0), s1=H(t1), s2=H(t2),
                     eq01=(t0 == t1), eq12=(t1 == t2), eq02=(t0 == t2),
                     chg0=c0, chg1=c1, samples=[x for x in (t0.split('\r\n')) if
                                                any('\u4e00' <= c <= '\u9fff' for c in x)][:3]))
iso.close()
for r in rows:
    print('%-34s blob %-7d slot %-7d\n    slot_sha  %s\n    G0/G1/G2  %s %s %s   eq(0,1)=%s eq(1,2)=%s eq(0,2)=%s\n'
          '    陈旧→现役改字节 %d (编不出 %d/长度不等 %d);  G1→现役改字节 %d (编不出 %d/长度不等 %d)'
          % (r['key'], r['blob'], r['slot'], r['slot_sha'], r['s0'], r['s1'], r['s2'],
             r['eq01'], r['eq12'], r['eq02'], r['chg0'][0], r['chg0'][1], r['chg0'][2],
             r['chg1'][0], r['chg1'][1], r['chg1'][2]))
    for x in r['samples'][:2]:
        print('      | %r' % x[:90])
