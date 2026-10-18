import io, os, re, difflib
root = r'work\builds\GR_DFIX\runs'
tags = ['base','DFIX_pkt','DFIX_fp','DFIX_icon']
rx_ts = re.compile(r'^\[\s*\d+\.\d+\]\s?')
rx_hex = re.compile(r'0x[0-9A-Fa-f]+')
rx_ram = re.compile(r'Available RAM\s+= \d+ MB \([\d.]+ GB\)')
def lines(t):
    p = os.path.join(root, t, 'emulog.txt')
    out = []
    for l in io.open(p, encoding='utf-8', errors='replace').read().splitlines():
        l = rx_ts.sub('', l)
        l = rx_hex.sub('0x<ADDR>', l)
        l = rx_ram.sub('Available RAM = <N>', l)
        l = re.sub(r'\s+', ' ', l).strip()
        out.append(l)
    return out
b = lines('base')
print('base lines', len(b))
for t in tags[1:]:
    o = lines(t)
    d = [x for x in difflib.unified_diff(b, o, lineterm='', n=0) if x.startswith(('+','-')) and not x.startswith(('+++','---'))]
    print(t, 'lines', len(o), 'normalized_diff_lines', len(d))
    for x in d[:6]:
        print('   ', x[:200])
