# -*- coding: utf-8 -*-
import sys
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
cs = T.Charset()
sbcodes = sorted(cs.codes)
def cls(r):
    if r[2] >= 992: return 'STRIP'
    if 194 <= r[3] <= 241: return 'skipband'
    return 'gridrow'
for (fn, fld, rows) in faces:
    print('==== face', fn)
    prev = None; start = None
    segs = []
    for k, (o, r) in enumerate(rows):
        c = cls(r)
        if c != prev:
            if prev is not None: segs.append((start, k-1, prev))
            prev, start = c, k
    segs.append((start, len(rows)-1, prev))
    for (a, b, c) in segs:
        rs = [rows[i][1] for i in range(a, b+1)]
        print('   idx %3d..%-3d (code 0x%02X..0x%02X) %-9s u %4d..%-4d v %4d..%-4d n=%d ink=%d'
              % (a, b, a+0x20, b+0x20, c, min(r[2] for r in rs), max(r[4] for r in rs),
                 min(r[3] for r in rs), max(r[5] for r in rs), b-a+1,
                 sum(int(img[r[3]:r[5], r[2]:r[4]].sum()) for r in rs)))
    print('   —— 其中「码位在本盘单字节码表里」的 idx 数: %d / %d'
          % (sum(1 for k in range(len(rows)) if (k+0x20) in cs.codes), len(rows)))
    print('   —— 单字节码表里的码 (0x80..0xFF) → idx %s..%s'
          % (sbcodes[0]-0x20, sbcodes[-1]-0x20))
