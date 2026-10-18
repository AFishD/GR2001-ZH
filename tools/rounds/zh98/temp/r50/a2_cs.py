import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
cs = json.load(io.open(os.path.join(REPO,'tools/font_pipeline/data/charset_compiled_zh16.json'), encoding='utf-8'))
print('keys:', list(cs.keys()))
print('codes:', len(cs['codes']), 'pair_of:', len(cs['pair_of']))
for ch in '孙宁宇±®':
    print(repr(ch), 'code=', cs['codes'].get(ch), 'pair=', cs['pair_of'].get(ch))
nonhan = [ (ch,tuple(v)) for ch,v in cs['pair_of'].items() if not ('\u4e00' <= ch <= '\u9fff') ]
print('pair 非汉字:', len(nonhan), ''.join(c for c,_ in nonhan))
print(' '.join('%s=%02X%02X' % (c, v[0], v[1]) for c,v in nonhan))
