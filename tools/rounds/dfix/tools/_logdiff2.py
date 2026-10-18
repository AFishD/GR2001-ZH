import io, os, re, difflib
root = r'work\builds\GR_DFIX\runs'
tags = ['base','DFIX_pkt','DFIX_fp','DFIX_icon']
noise = re.compile(r'isoFile|Disc changed|Fastmem|GameDB|Available RAM|_base\.iso|DFIX_|\.iso|^Cover|^ISO|GameDB')
rx_ts = re.compile(r'^\[\s*\d+\.\d+\]\s?')
def lines(t):
    p = os.path.join(root, t, 'emulog.txt')
    out = []
    for l in io.open(p, encoding='utf-8', errors='replace').read().splitlines():
        l = rx_ts.sub('', l)
        l = re.sub(r'0x[0-9A-Fa-f]+', '0x<A>', l)
        l = re.sub(r'\b[0-9A-F]{8,}\b', '<A>', l)
        l = re.sub(r'\d+(\.\d+)?\s*(ms|MB|GB)\b', '<N>', l)
        l = re.sub(r'\s+', ' ', l).strip()
        out.append(l)
    return out
b = lines('base')
for t in tags[1:]:
    o = lines(t)
    d = [x for x in difflib.unified_diff(b, o, lineterm='', n=0) if x.startswith(('+','-')) and not x.startswith(('+++','---'))]
    real = [x for x in d if not noise.search(x)]
    print('==', t, 'diff', len(d), 'non-noise', len(real))
    for x in real[:40]:
        print('   ', x[:180])
