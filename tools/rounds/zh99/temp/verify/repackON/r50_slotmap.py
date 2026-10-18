import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work/builds/GR_ZH99/temp/verify')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib, dump_font
import numpy as np
from PIL import Image, ImageDraw, ImageFont
CS98 = tcslib.Charset(os.path.join(HERE, 'charset_zh98.json'))
CS99 = tcslib.Charset(os.path.join(HERE, 'charset_zh99.json'))
def atlas(rel):
    f = dump_font.load_font(os.path.join(REPO, rel))
    g = dump_font.atlas_gray(f['atlas'], view='engine')
    w, h = f['atlas']['w'], f['atlas']['h']
    return (np.frombuffer(g, np.uint8).reshape(h, w) == 0)
A99 = atlas('work/builds/GR_ZH99/GR_ZH99.iso')
A98 = atlas('work/builds/GR_ZH98/GR_ZH98.iso')
for code in [(0xa6,0xa6),(0xa6,0xa7),(0xa5,0xce),(0xa5,0xcf),(0xa8,0xce),(0xa8,0xd2)]:
    slot = tcslib.pair_slot(*code)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    print('码 %02X%02X slot=%4d row=%2d col=%2d | ZH98charset说=%-3r ZH99charset说=%-3r | 两版图集这一格是否相同=%s'
          % (code[0], code[1], slot, slot//62, slot%62,
             CS98.pair_of.get(code), CS99.pair_of.get(code),
             bool(np.array_equal(A98[y:y+16, x:x+16], A99[y:y+16, x:x+16]))))
