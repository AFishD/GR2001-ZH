# -*- coding: utf-8 -*-
import collections, sys
sys.path.insert(0, r'tools\re\toolbelt'); sys.path.insert(0, r'tools\text_csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T, zx_lib
iso = T.Iso(r'work\builds\GR_ZH124\GR_ZH124.iso')
ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
eft = [x for x in ent if x['name']=='FONT.RES'][0]
ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(eft['iso_off'], eft['stored']))))
faces, endp = zx_lib.ft_records(ft, 28)
strip = {}
for (fn, fld, rows) in faces:
    for k, (o, r) in enumerate(rows):
        if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
            strip.setdefault(r, []).append((fn, k))
print('STRIP 不同矩形数 =', len(strip))
print('引用者 (face, idx) 前 6 个:', [v[:6] for v in list(strip.values())[:6]])
areas = collections.Counter((r[4]-r[2], r[5]-r[3]) for r in strip)
print('矩形尺寸分布:', dict(areas))
tot = sum((r[4]-r[2])*(r[5]-r[3]) for r in strip)
print('STRIP 总 texel =', tot, ' = %.1f 个 16x16 格' % (tot/256.0))
# skip band 占用
import numpy as np
cov = np.zeros((512, 1024), dtype=bool)
for (fn, fld, rows) in faces:
    for k, (o, r) in enumerate(rows):
        if r[4] > r[2] and r[5] > r[3] and 194 <= r[3] < 242:
            cov[r[3]:r[5], r[2]:r[4]] = True
band = cov[194:242, :]
print('skip band y194..241: 覆盖 texel %d / %d (%.1f%%)' % (band.sum(), band.size, 100.0*band.sum()/band.size))
# 逐 8px 列 × 16px 行的空闲格 (8x16 粒度, 覆盖 strip 的 8 宽矩形)
free = []
for y in (194, 210, 226):
    for x in range(0, 1024, 8):
        if not cov[y:y+16, x:x+8].any():
            free.append((x, y))
print('skip band 内 8x16 全空格数 =', len(free))
free16 = []
for y in (194, 210, 226):
    for x in range(0, 1024, 16):
        if not cov[y:y+16, x:x+16].any():
            free16.append((x, y))
print('skip band 内 16x16 全空格数 =', len(free16))
print('空闲 8x16 前 24 个:', free[:24])
# 每行 8x16 粒度免费数
for y in (194, 210, 226):
    n = sum(1 for (x, yy) in free if yy == y)
    print('   y=%d : %d 个空闲 8x16' % (y, n))
