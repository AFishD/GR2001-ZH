import base64, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
d = json.load(io.open(os.path.join(REPO,'work/builds/GR_ZH98/temp/font_recycle_backup.json'), encoding='utf-8'))
g = d['glyphs']
def show(ch, bits_b64):
    b = base64.b64decode(bits_b64)
    rows = [b[i*2] for i in range(16)]   # 16 rows x 16 bits? check length
    print(' len=', len(b))
    # bits likely 16 rows * 2 bytes = 32 bytes, MSB first per row
    for r in range(16):
        w = (b[r*2] << 8) | b[r*2+1]
        print('  %2d %s' % (r, ''.join('#' if (w >> (15-c)) & 1 else '.' for c in range(16))))
for ch in '孙宁宇':
    e = g[ch]
    print('==', ch, 'pair=%02X%02X slot=%d cell=%s ink=%d' % (e['pair'][0], e['pair'][1], e['slot'], e['cell'], e['ink_px']))
    show(ch, e['bits'])
