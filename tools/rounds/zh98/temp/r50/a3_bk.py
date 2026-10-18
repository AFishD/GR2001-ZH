import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
d = json.load(io.open(os.path.join(REPO,'work/builds/GR_ZH98/temp/font_recycle_backup.json'), encoding='utf-8'))
print('chars:', d['chars'])
g = d['glyphs']
k0 = list(g.keys())[0]
print('glyph keys sample:', list(g.keys())[:6])
print('one entry type:', type(g[k0]).__name__)
e = g[k0]
if isinstance(e, dict):
    for kk, vv in e.items():
        print('   ', kk, '=', (vv if not isinstance(vv,(list,dict)) or len(str(vv))<120 else str(vv)[:120]+'...'))
