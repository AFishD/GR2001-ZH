import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
files = [
 ('ZH92-94 disk','work/builds/GR_ZH94/font/charset_matching_this_disk.json'),
 ('ZH95 before-repack','work/builds/GR_ZH95/temp/r46/charset_before_repack.json'),
 ('ZH95 after-repack','work/builds/GR_ZH95/temp/r46/charset_after_repack.json'),
 ('ZH95 font_repack/before','work/builds/GR_ZH95/temp/font_repack/charset_before.json'),
 ('ZH97 pre-cleanup','work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'),
 ('ZH98 current','tools/font_pipeline/data/charset_compiled_zh16.json'),
]
targets = '叶奋姚娜孙宁宇±'
print('%-26s %s' % ('charset', '  '.join('%-8s' % c for c in targets)))
for tag, rel in files:
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        print('%-26s (missing)' % tag); continue
    js = json.load(io.open(p, encoding='utf-8'))
    po = js['pair_of']
    cells = []
    for c in targets:
        v = po.get(c)
        cells.append(('%02X%02X' % (v[0], v[1])) if v else '-none-')
    print('%-26s %s   (pair=%d)' % (tag, '  '.join('%-8s' % x for x in cells), len(po)))
