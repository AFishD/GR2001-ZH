import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
p = os.path.join(REPO, 'work/builds/GR_ZH98/temp/font_recycle_backup.json')
d = json.load(io.open(p, encoding='utf-8'))
print('top keys:', list(d.keys())[:20])
for k in list(d.keys()):
    v = d[k]
    print(' ', k, type(v).__name__, (len(v) if hasattr(v,'__len__') else ''))
