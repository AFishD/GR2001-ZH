# -*- coding: utf-8 -*-
"""Analyze Ghost Recon PC Chinese font assets (read-only)."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct, os, sys, collections

BASE = os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon')
ART = os.path.join(BASE, 'Data', 'Shell', 'Art')
OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'pcfont')

def rd(p):
    return open(p, 'rb').read()

# ---------- 1. charset tables ----------
def load_charset(path):
    d = rd(path)
    return d

cd = rd(os.path.join(BASE, 'Chinese.dat'))
print('Chinese.dat: %d bytes' % len(cd))
s_cd = cd.decode('gbk')
print('  chars=%d unique=%d' % (len(s_cd), len(set(s_cd))))
cp_cd = set(ord(c) for c in s_cd)

gd = rd(os.path.join(ART, 'gbtext.def'))
print('gbtext.def: %d bytes' % len(gd))
print('  first16:', gd[:16].hex())
# try as raw GBK pairs
s_gd = gd.decode('gbk', errors='replace')
print('  decoded len=%d unique=%d' % (len(s_gd), len(set(s_gd))))
cp_gd = set(ord(c) for c in s_gd if ord(c) >= 0x4e00)
print('  CJK unique=%d' % len(cp_gd))
print('  overlap with Chinese.dat: %d' % len(cp_gd & cp_cd))
print('  gbtext-only: %d  chinese.dat-only: %d' % (len(cp_gd - cp_cd), len(cp_cd - cp_gd)))

# ---------- 2. TGA headers ----------
for f in ['GB1200.tga', 'GB1600.tga', 'GB1601.tga', 'GB2400.tga', 'GB2401.tga', 'GB2402.tga']:
    d = rd(os.path.join(ART, f))
    idlen, cmap, imgtype = d[0], d[1], d[2]
    w, h = struct.unpack('<HH', d[12:16])
    bpp, desc = d[16], d[17]
    print('%s: idlen=%d cmap=%d type=%d %dx%d bpp=%d desc=0x%02x size=%d' %
          (f, idlen, cmap, imgtype, w, h, bpp, desc, len(d)))
    if idlen:
        print('   id:', d[18:18+idlen])

# ---------- 3. RSB header ----------
for f in ['Chinese0.rsb', 'gb1200.rsb', 'gb2400.rsb', 'new_font_revised.rsb']:
    d = rd(os.path.join(ART, f))
    print('%s: size=%d' % (f, len(d)))
    print('   head64:', d[:64].hex())
    printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:120])
    print('   ascii:', printable)
