import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
for v in ('GR_ZH97', 'GR_ZH98'):
    p = os.path.join(REPO, 'work/builds', v, 'build_info.json')
    d = json.load(io.open(p, encoding='utf-8'))
    print('=== %s' % v)
    print('  keys:', [k for k in d.keys()])
    fr = d.get('font_repack')
    print('  font_repack:', json.dumps(fr, ensure_ascii=False)[:700] if fr else None)
    print('  iso_sha256:', d.get('iso_sha256') or d.get('sha256'))
cs = json.load(io.open(os.path.join(REPO,'tools/font_pipeline/data/charset_compiled_zh16.json'), encoding='utf-8'))
print('charset _font_repack:', json.dumps(cs.get('_font_repack'), ensure_ascii=False)[:500])
print('charset _font_recycle_zh98:', json.dumps(cs.get('_font_recycle_zh98'), ensure_ascii=False)[:400])
