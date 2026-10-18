import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TD = os.path.join(REPO, 'work/builds/GR_ZH98/text')
ctrl = '李明王约翰逊'
targets = '孙宁宇叶奋姚娜'
for fn in sorted(os.listdir(TD)):
    if not fn.endswith('.csv'):
        continue
    p = os.path.join(TD, fn)
    raw = io.open(p, 'rb').read()
    try:
        txt = raw.decode('utf-8-sig')
    except UnicodeDecodeError as e:
        txt = raw.decode('gbk', errors='replace')
        print('  [gbk] %s' % fn)
    c = {k: txt.count(k) for k in ctrl}
    t = {k: txt.count(k) for k in targets}
    print('%-42s ctrl=%s  目标=%s' % (fn, c, t))
