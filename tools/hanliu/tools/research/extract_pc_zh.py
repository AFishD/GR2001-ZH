# -*- coding: utf-8 -*-
"""Extract ALL Chinese text from PC official resources: strings.txt (GBK key->value),
STRINGS.RES (keyed blocks, tolerant scan), Chinese.dat (raw GBK fragments).
Output: pc_zh_corpus.txt (one line per unit), pc_zh_stats.json"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct, re, json, collections

OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand')
CJK = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')

def gbk(b):
    return b.decode('gbk', 'replace')

units = []  # (source, key, text)

# 1) strings.txt
st = open(os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon', 'Data', 'Shell', 'strings.txt'), 'rb').read().decode('gbk', 'replace')
for m in re.finditer(r'"([^"]+)"\s*"([^"]*)"', st):
    units.append(('strings.txt', m.group(1), m.group(2)))

# 2) STRINGS.RES tolerant block scan
d = open(os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon', 'Data', 'Shell', 'STRINGS.RES'),'rb').read()
keys = []
i = 4
while i < len(d) - 4:
    klen = struct.unpack_from('<I', d, i)[0]
    if 1 <= klen <= 64 and i+4+klen <= len(d):
        kb = d[i+4:i+4+klen]
        if all(0x20 <= b <= 0x7e for b in kb) and re.fullmatch(r'[A-Za-z0-9_ /:.\'\-]+', kb.decode('latin-1')):
            keys.append((i, klen, kb.decode('latin-1')))
            i += 4 + klen
            continue
    i += 1
for n, (pos, kl, k) in enumerate(keys):
    end = keys[n+1][0] if n+1 < len(keys) else len(d)
    blob = d[pos+4+kl:end]
    # strip leading {u32 klen?}{nul} remnants and length fields conservatively: just decode all, then clean
    txt = gbk(blob)
    # split on NULs / control chars
    for seg in re.split(r'[\x00-\x08\x0b-\x1f]+', txt):
        seg = seg.strip('\ufffd')
        if CJK.search(seg):
            units.append(('STRINGS.RES', k, seg))

# 3) Chinese.dat
cd = open(os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon', 'Chinese.dat'),'rb').read().decode('gbk','replace')
for seg in re.split(r'[\x00-\x08\x0b-\x1f]+', cd):
    if CJK.search(seg):
        units.append(('Chinese.dat', '', seg))

with open(OUT + r'\pc_zh_corpus.txt', 'w', encoding='utf-8') as f:
    for src, k, t in units:
        f.write(f'{src}\t{k}\t{t}\n')

# distinct hanzi (only CJK ideographs, exclude punctuation)
han = collections.Counter()
fullpunct = collections.Counter()
for src, k, t in units:
    for ch in t:
        if '\u4e00' <= ch <= '\u9fff':
            han[ch] += 1
        elif ch in '\u3000-\u303f\uff00-\uffef\u2014\u2018\u2019\u201c\u201d\u2026':
            fullpunct[ch] += 1
stats = {
    'units': len(units),
    'total_cjk_chars': sum(han.values()),
    'distinct_hanzi': len(han),
    'fullwidth_punct': {c: n for c, n in fullpunct.most_common()},
}
json.dump({'stats': stats, 'freq': han.most_common()}, open(OUT + r'\pc_zh_stats.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps(stats, ensure_ascii=False, indent=1))
print('top 40:', ''.join(c for c, n in han.most_common(40)))
