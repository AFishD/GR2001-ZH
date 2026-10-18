# -*- coding: utf-8 -*-
r"""probe6.py — 逐类别 × 逐阈值: 英文原盘(对照)与中文盘各自命中多少字

目的: 用**英文原盘**定标每一类容器该用什么阈值 —— 让对照盘的假阳性降到 0 (或极小)。
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

TH = (4, 8, 12, 16, 24, 32, 48, 64, 96, 128)
idx = F.CharsetIndex()


def scan_disc(path, tag):
    iso = T.Iso(path)
    cs = F.build_container_list(iso)
    res = {}
    t0 = time.time()
    for n, c in enumerate(cs):
        blob, _raw = F.container_blob(iso, c)
        hits = {t: set() for t in TH}
        for m in idx.run_re(4).finditer(blob):
            L = m.end() - m.start()
            for ch in idx.decode_chars(m.group(0)):
                for t in TH:
                    if L >= t:
                        hits[t].add(ch)
        d = res.setdefault(c['kind'], {t: set() for t in TH})
        d['n'] = d.get('n', 0) + 1
        d['blob'] = d.get('blob', 0) + len(blob)
        for t in TH:
            d[t] |= hits[t]
        if (n + 1) % 1500 == 0:
            print('   %s %d/%d (%.0fs)' % (tag, n + 1, len(cs), time.time() - t0))
    iso.close()
    return res


out = {}
for path, tag in ((os.path.join(REPO, 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso'), 'EN'),
                  (os.path.join(REPO, 'work/builds/GR_ZH92/GR_ZH92.iso'), 'ZH')):
    print('== %s ==' % tag)
    out[tag] = scan_disc(path, tag)

kinds = sorted(set(out['EN']) | set(out['ZH']),
               key=lambda k: -out['ZH'].get(k, {}).get('blob', 0))
hdr = '%-10s %5s %10s | ' % ('kind', 'n', 'MB') + ' '.join('%5d' % t for t in TH)
print('\n英文原盘(对照) 命中字数  ← 这些全是假阳性')
print(hdr)
for k in kinds:
    d = out['EN'].get(k)
    if not d:
        continue
    print('%-10s %5d %10.1f | ' % (k, d['n'], d['blob'] / 1048576)
          + ' '.join('%5d' % len(d[t]) for t in TH))
print('\n中文盘 命中字数')
print(hdr)
for k in kinds:
    d = out['ZH'].get(k)
    if not d:
        continue
    print('%-10s %5d %10.1f | ' % (k, d['n'], d['blob'] / 1048576)
          + ' '.join('%5d' % len(d[t]) for t in TH))

json.dump({tag: {k: {str(t): sorted(v[t]) for t in TH} | {'n': v['n'], 'blob': v['blob']}
                 for k, v in out[tag].items()} for tag in out},
          open(os.path.join(REPO, 'work/builds/GR_ZH92/temp/r38/perkind.json'), 'w',
               encoding='utf-8'), ensure_ascii=False)
print('\n-> perkind.json')
