# -*- coding: utf-8 -*-
import collections, sys
sys.path.insert(0, r'tools\re\toolbelt'); sys.path.insert(0, r'tools\text_csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T, zx_lib
def yrow(r): return 2 + 16*(r + (3 if r >= 12 else 0))
def rows_fit(h):
    r = 0
    while yrow(r)+16 <= h: r += 1
    return r
grid = set()
for r in range(rows_fit(644)):
    grid.update(range(yrow(r), yrow(r)+16))
iso = T.Iso(r'work\builds\GR_ZH124\GR_ZH124.iso')
ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
e = [x for x in ent if x['name']=='COMMON.PAK'][0]
eft = [x for x in ent if x['name']=='FONT.RES'][0]
pak = bytes(iso.read(e['iso_off'], e['stored']))
r1 = T.parse_pak_records(pak)[1]
img, cov = zx_lib.decode_engine(bytes(pak[r1[6]:r1[6]+r1[5]]), 1024, 512)
ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(eft['iso_off'], eft['stored']))))
faces, _ = zx_lib.ft_records(ft, 28)
over = []
for (fn, fld, rows) in faces:
    for k, (o, r) in enumerate(rows):
        if r[4] <= r[2] or r[5] <= r[3]: continue
        if any(y in grid for y in range(r[3], r[5])):
            over.append((fn, k, r))
print('overlap records:', len(over))
c = collections.Counter((r[2], r[4], r[3], r[5]) for (_f,_k,r) in over)
for k, n in sorted(c.items()):
    print('  u %4d..%-4d v %4d..%-4d  x%d' % (k[0],k[1],k[2],k[3],n))
print('face:', collections.Counter(f for (f,_k,_r) in over))
print('idx range:', min(k for (_f,k,_r) in over), max(k for (_f,k,_r) in over))
print('base ink x992..1023 y0..511 :', int(img[0:512, 992:1024].sum()))
print('base ink x992..1023 y0..497 :', int(img[0:498, 992:1024].sum()))
w = sum(1 for (_f,_k,r) in over if img[r[3]:r[5], r[2]:r[4]].sum())
print('168 overlap rects on BASE: 有墨 %d / 无墨 %d' % (w, len(over)-w))
for (fn,k,r) in over[:6]:
    print('   e.g. face=%s idx=%d code=0x%02X u%4d..%-4d v%4d..%-4d ink=%d' % (fn,k,k+0x20,r[2],r[4],r[3],r[5],int(img[r[3]:r[5], r[2]:r[4]].sum())))
