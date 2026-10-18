# -*- coding: utf-8 -*-
import collections, sys
sys.path.insert(0, r'tools\re\toolbelt'); sys.path.insert(0, r'tools\text_csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T, zx_lib
iso = T.Iso(r'work\builds\GR_ZH124\GR_ZH124.iso')
ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
eft = [x for x in ent if x['name']=='FONT.RES'][0]
e = [x for x in ent if x['name']=='COMMON.PAK'][0]
pak = bytes(iso.read(e['iso_off'], e['stored']))
r1 = T.parse_pak_records(pak)[1]
img, cov = zx_lib.decode_engine(bytes(pak[r1[6]:r1[6]+r1[5]]), 1024, 512)
ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(eft['iso_off'], eft['stored']))))
faces, endp = zx_lib.ft_records(ft, 28)
for (fn, fld, rows) in faces:
    ne = [(k, r) for k,(o,r) in enumerate(rows) if r[4] > r[2] and r[5] > r[3]]
    print('==== face %s : nrec=%d 非空=%d  fld=%s' % (fn, fld[4]*fld[5], len(ne), fld))
    band = collections.Counter()
    for k, r in ne:
        if r[2] >= 992: b = 'right-edge x>=992'
        elif r[3] >= 448: b = 'y>=448'
        elif 194 <= r[3] <= 241: b = 'skipband y194..241'
        elif any(2+16*(q+(3 if q>=12 else 0)) <= r[3] < 2+16*(q+(3 if q>=12 else 0))+16 for q in range(28)): b='grid row y'
        else: b = 'other y=%d' % r[3]
        band[b] += 1
    for b, n in band.most_common():
        print('    %-24s %3d' % (b, n))
    # u 范围 / v 范围 per band
    for b in band:
        rs = [r for k,r in ne if (('right-edge' in b and r[2]>=992) or ('skipband' in b and 194<=r[3]<=241 and r[2]<992) or ('grid row' in b and r[2]<992 and not (194<=r[3]<=241) and not any(2+16*(q+(3 if q>=12 else 0)) <= r[3] < 2+16*(q+(3 if q>=12 else 0))+16 for q in range(0))) )]
        if rs and 'right-edge' in b:
            print('       right-edge: u %d..%d v %d..%d n=%d ink=%d' % (min(r[2] for r in rs), max(r[4] for r in rs), min(r[3] for r in rs), max(r[5] for r in rs), len(rs), sum(int(img[r[3]:r[5], r[2]:r[4]].sum()) for r in rs)))
print()
print('=== ink 在 x992..1023 的逐 y 分布 (只看有墨) ===')
for y in range(512):
    n = int(img[y, 992:1024].sum())
    if n: print('   y=%3d ink=%2d' % (y, n))
