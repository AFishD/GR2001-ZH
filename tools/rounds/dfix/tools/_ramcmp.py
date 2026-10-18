import glob, hashlib, os, re
root = r'work\builds\GR_DFIX\runs'
tags = ['base','DFIX_pkt','DFIX_fp','DFIX_icon']
def hs(d):
    out = {}
    for p in glob.glob(os.path.join(root, d, '*_eeram.bin')):
        h = hashlib.sha256()
        with open(p,'rb') as f:
            for b in iter(lambda: f.read(1<<20), b''):
                h.update(b)
        out[os.path.basename(p)] = h.hexdigest()
    return out
base = hs('base')
print('base eeram dumps:', len(base))
for t in tags[1:]:
    o = hs(t)
    common = sorted(set(base) & set(o))
    same = sum(1 for k in common if base[k]==o[k])
    print('%s: dumps=%d common=%d identical=%d' % (t, len(o), len(common), same))
    for k in common:
        if base[k]!=o[k]:
            print('   DIFF', k)
    if set(base)^set(o):
        print('   only-base', sorted(set(base)-set(o)), 'only-run', sorted(set(o)-set(base)))
