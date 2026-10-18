import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TD = os.path.join(REPO, 'work/builds/GR_ZH98/text')
targets = '孙宁宇叶奋姚娜'
for fn in sorted(os.listdir(TD)):
    if not fn.endswith('.csv'):
        continue
    p = os.path.join(TD, fn)
    txt = io.open(p, encoding='utf-8-sig', errors='replace').read()
    hits = {c: txt.count(c) for c in targets if c in txt}
    print('%-42s %s' % (fn, hits or ''))
