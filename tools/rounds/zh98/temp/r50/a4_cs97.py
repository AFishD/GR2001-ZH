import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
cs = json.load(io.open(os.path.join(REPO,'work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'), encoding='utf-8'))
print('before-cleanup: codes', len(cs['codes']), 'pair_of', len(cs['pair_of']))
for ch in '孙宁宇±®':
    print(repr(ch), 'code=', cs['codes'].get(ch), 'pair=', cs['pair_of'].get(ch))
print('recycle meta:', json.dumps(cs.get('_font_recycle_zh98'), ensure_ascii=False)[:600])
