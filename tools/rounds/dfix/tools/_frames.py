import glob, hashlib, os, re, collections
d = r'work\builds\GR_DFIX\runs\base'
hs = collections.OrderedDict()
for p in sorted(glob.glob(os.path.join(d,'snap_*.png'))):
    h = hashlib.sha256(open(p,'rb').read()).hexdigest()
    hs.setdefault(h, []).append((int(re.search(r'(\d+)\.png', p).group(1)), os.path.getsize(p)))
print('unique scenes:', len(hs))
for h, v in hs.items():
    fs = [x[0] for x in v]
    # compress to ranges
    rng, start, prev = [], fs[0], fs[0]
    for f in fs[1:]:
        if f == prev + 30: prev = f; continue
        rng.append((start, prev)); start = prev = f
    rng.append((start, prev))
    print('%s x%-3d size=%-7d %s' % (h[:12], len(fs), v[0][1], ' '.join('%d-%d' % r if r[0]!=r[1] else '%d' % r[0] for r in rng)))
