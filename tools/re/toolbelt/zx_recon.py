# -*- coding: utf-8 -*-
r"""zx_recon.py — 「零缺字成品盘」第 2 轮 (round82) 只读侦察。

只读，不写任何盘。产出 work/builds/GR_ZH98/temp/r82/recon2.txt。

覆盖：
  [1] MENU.IMG 头 12 u32 + 条目记录 12 u32 的真实字段布局（哪一种镜像形态）
  [2] COMMON.PAK 4 条记录 + new_font_revised 像素容器分段
  [3] FONT.RES 3 个 face 的逐记录矩形分布（按 (u0,v0,u1,v1) 归组）
  [4] 「两条活带」的精确矩形并集（旧的 y=452/482 带）+ 单字节码 0xB1..0xB4 的记录
  [5] ISO9660 根目录记录（MENU.IMG;1）+ MENU.IMG 尾料算术
  [6] 4 处 ELF gate 站点逐字节
  [7] 条目物理布局：COMMON.PAK 之后紧跟哪些条目，off ≥ 0xB9120 的条目数
  [8] 新格位表 (slot 1504..1871 → row/col/x/y) 与旧带重叠检查
"""
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
os.makedirs(OUT, exist_ok=True)
MENU_LBA = tcslib.MENU_LBA
SEC = 2048
W, H = 1024, 512

buf = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    buf.append(s)


iso = tcslib.Iso(ISO)
base = MENU_LBA * SEC

P('=' * 78)
P('[1] MENU.IMG 头 + 条目记录字段布局')
P('=' * 78)
hdr = struct.unpack_from('<12I', iso.mm, base)
P('  头 12 u32: %s' % ' '.join('0x%X' % v for v in hdr))
P('    size=0x%X names_end=0x%X sector=0x%X tbl_end=0x%X names_start=0x%X data_start=0x%X'
  % (hdr[0], hdr[1], hdr[2], hdr[3], hdr[4], hdr[5]))

TAB_OFF, TAB_STEP = 0x830, 48
names = []
for i in range(2000):
    e = iso.img_entry(MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
P('  条目数 = %d（表 0x%X .. 0x%X = 0x%X，期望表末 0x%X）'
  % (len(names), TAB_OFF, TAB_OFF + TAB_STEP * len(names), TAB_OFF + TAB_STEP * len(names), hdr[3]))

for i in list(range(6)) + [len(names) - 1]:
    raw = struct.unpack_from('<12I', iso.mm, base + TAB_OFF + TAB_STEP * i)
    P('  #%-3d %-26s raw=%s' % (i, names[i], ' '.join('%08X' % v for v in raw)))
    P('       [LE/BE 判读] ' + ' | '.join(
        'f%d LE=%u BE=%u' % (k, raw[2 * k], struct.unpack('>I', struct.pack('<I', raw[2 * k + 1]))[0])
        for k in range(6)))

# 用 #3 COMMON.PAK (stored=400659 off=0x57400) 反推哪个下标是 stored / real / off
for i in range(len(names)):
    raw = struct.unpack_from('<12I', iso.mm, base + TAB_OFF + TAB_STEP * i)
    if names[i] == 'COMMON.PAK':
        P('  ★ COMMON.PAK #%d raw = %s' % (i, ' '.join('%08X' % v for v in raw)))
        for k, v in enumerate(raw):
            P('      u32[%2d] = %-12d 0x%X' % (k, v, v))
        break

P('')
P('=' * 78)
P('[2] COMMON.PAK 记录 + 像素容器分段')
P('=' * 78)
pak_e = None
for i in range(len(names)):
    if names[i] == 'COMMON.PAK':
        pak_e = iso.img_entry(MENU_LBA, i)
        pak_i = i
        break
pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
recs = tcslib.parse_pak_records(bytes(pak))
P('  COMMON.PAK #%d off=0x%X stored=%d' % (pak_i, pak_e['off'], pak_e['stored']))
for k, r in enumerate(recs):
    P('    rec#%d %-20s psm=0x%02X %dx%d clut=0x%X px_size=0x%X px_off=0x%X end=0x%X'
      % (k, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[6] + r[5]))
nm, psm, aw, ah, clut, px_size, PX = recs[1]
segs = tcslib.atlas_container_segments(bytes(pak[PX:PX + px_size]), W // 2)
P('  new_font_revised: px_size=0x%X = %d ; parse_pak 结束 = 0x%X' % (px_size, px_size, r[6] + r[5]))
P('  分段 %d 个:' % len(segs))
for k, (fr, doff, nb) in enumerate(segs):
    P('     seg%d 首行=%-4d doff=0x%-7X bytes=%-7d (%.2f 行)' % (k, fr, doff, nb, nb / 512.0))
P('  段前缀 = 0x%X, 数据合计 = %d, 理论 px_size = %d*48 + %d + 16 = %d'
  % (segs[0][1], sum(s[2] for s in segs), len(segs), sum(s[2] for s in segs),
     len(segs) * 48 + sum(s[2] for s in segs) + 16))
P('  段0 头 48B: %s' % ' '.join('%02X' % b for b in pak[PX:PX + 48]))
P('  尾部 16B  : %s' % ' '.join('%02X' % b for b in pak[PX + px_size - 16:PX + px_size]))

P('')
P('=' * 78)
P('[3] FONT.RES 逐记录矩形')
P('=' * 78)
ft_e = None
for i in range(len(names)):
    if names[i] == 'FONT.RES':
        ft_e = iso.img_entry(MENU_LBA, i)
        ft_i = i
        break
ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
subs = tcslib.lzo_subs(ft_slot)
exp = b''.join(s[0] for s in subs)
he, faces = tcslib.parse_ft_faces(exp)
P('  FONT.RES #%d off=0x%X stored=%d real=%d ; 子流 %d 个, 展开 %d B ; faces 结束 @0x%X'
  % (ft_i, ft_e['off'], ft_e['stored'], ft_e['real'], len(subs), len(exp), he))
P('  子流明细: %s' % [(s[1], s[2]) for s in subs])
for (nm2, fld, rs) in faces:
    P('  --- face %r nrec=%d fld=%s' % (nm2, fld[4] * fld[5], fld))
    groups = {}
    for r_i, r in enumerate(rs):
        key = (r[2], r[3], r[4], r[5])
        groups.setdefault(key, []).append(r_i)
    for key in sorted(groups, key=lambda k: (k[1], k[0])):
        idx = groups[key]
        P('      rect(u0=%4d v0=%4d u1=%4d v1=%4d) x%-3d  idx %s'
          % (key[0], key[1], key[2], key[3], len(idx),
             ('%d..%d' % (idx[0], idx[-1])) if len(idx) > 2 else str(idx)))
    P('      (b0,b1) 直方图: %s' % sorted({(r[0], r[1]): sum(1 for q in rs if q[:2] == r[:2])
                                          for r in rs}.items())[:12])
    # 单字节码 0xB1..0xB4 → idx = code-0x20
    for code in (0xB1, 0xB2, 0xB3, 0xB4, 0xB5):
        idx = code - 0x20
        if idx < len(rs):
            r = rs[idx]
            P('      ★ code 0x%02X → rec[%d] = (b0=%d b1=%d u0=%d v0=%d u1=%d v1=%d)'
              % (code, idx, r[0], r[1], r[2], r[3], r[4], r[5]))
    # ASCII 0x41 'A' / 0x30 '0'
    for code in (0x41, 0x30, 0x20):
        idx = code - 0x20
        r = rs[idx]
        P('        ASCII 0x%02X → rec[%d] = (u0=%d v0=%d u1=%d v1=%d)'
          % (code, idx, r[2], r[3], r[4], r[5]))

P('')
P('=' * 78)
P('[4] 两条活带的矩形并集 + 单字节带')
P('=' * 78)
for band in ((452, 468), (482, 498), (195, 211), (211, 224), (211, 227), (213, 229)):
    for (nm2, fld, rs) in faces:
        hit = [r for r in rs if (r[3], r[5]) == band and r[4] > r[2]]
        if not hit:
            continue
        us = sorted({(r[2], r[4]) for r in hit})
        P('  face %-8s band(v0=%d,v1=%d) %3d 条 ; u 区间 %d..%d ; 采样窗 (+4,+2) = x[%d,%d) y[%d,%d)'
          % (nm2, band[0], band[1], len(hit), us[0][0], us[-1][1],
             us[0][0] + 4, us[-1][1] + 4, band[0] + 2, band[1] + 2))
        P('        u 起点: %s' % [u for u, _ in us][:12])

P('')
P('=' * 78)
P('[5] ISO9660 根目录 + MENU.IMG 尾料')
P('=' * 78)
pvd = 16 * SEC
vol = struct.unpack_from('<I', iso.mm, pvd + 80)[0]
root_lba = struct.unpack_from('<I', iso.mm, pvd + 158)[0]
root_sz = struct.unpack_from('<I', iso.mm, pvd + 166)[0]
P('  PVD vol_space=%d 扇区 = %d B ; 根目录 LBA=%d size=%d' % (vol, vol * SEC, root_lba, root_sz))
o = root_lba * SEC
while o < root_lba * SEC + root_sz:
    L = iso.mm[o]
    if L == 0:
        o = (o // SEC + 1) * SEC
        continue
    rec = bytes(iso.mm[o:o + L])
    nlen = rec[32]
    nm3 = rec[33:33 + nlen].decode('latin-1')
    lba = struct.unpack_from('<I', rec, 2)[0]
    be = struct.unpack_from('>I', rec, 6)[0]
    sz = struct.unpack_from('<I', rec, 10)[0]
    szbe = struct.unpack_from('>I', rec, 14)[0]
    flags = rec[25]
    P('  rec@0x%X len=%d %-16s LBA=%d size=%d (BE lba=%d size=%d) flags=0x%X  LBA_off=0x%X sizeLE_off=0x%X'
      % (o, L, nm3, lba, sz, be, szbe, flags, o + 2, o + 10))
    o += L
P('  MENU.IMG LBA=%d size=%d 占用扇区 %d ⇒ 到卷尾还剩 %d B'
  % (MENU_LBA, tcslib.Iso.img_entry(iso, MENU_LBA, 0) and 0 or 0, 0, 0))
mui = [f for f in []]
P('  MENU.IMG 清单: 用 IsoImage')
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import iso_tools  # noqa: E402
img = iso_tools.IsoImage(ISO)
for f in sorted(img.files, key=lambda x: x['lba']):
    P('    %s %-20s LBA=%-8d size=%-11d end=%d' % ('DIR ' if f['is_dir'] else 'FILE',
                                                   f['path'], f['lba'], f['size'],
                                                   f['lba'] * SEC + f['size']))
msize = [f for f in img.files if f['path'] == 'MENU.IMG;1'][0]['size']
P('  ★ MENU.IMG 可扩展上限 = %d - %d = %d B' % (vol * SEC - MENU_LBA * SEC, msize,
                                                vol * SEC - MENU_LBA * SEC - msize))

P('')
P('=' * 78)
P('[6] 4 处 ELF gate')
P('=' * 78)
ELF_ISO = 0x93880
for va in (0x416EE8, 0x417160, 0x41751C, 0x5656A4):
    off = ELF_ISO + va - 0x100000
    b = iso.read(off, 4)
    w = struct.unpack('<I', b)[0]
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    P('  VA 0x%06X ISO 0x%X  %s  op=0x%02X rs=%d rt=%d imm=0x%X'
      % (va, off, ' '.join('%02X' % x for x in b), op, rs, rt, imm))

P('')
P('=' * 78)
P('[7] 条目物理布局')
P('=' * 78)
ents = []
for i in range(len(names)):
    e = iso.img_entry(MENU_LBA, i)
    ents.append(e)
srt = sorted(range(len(ents)), key=lambda i: ents[i]['off'])
P('  物理顺序前 10:')
for k in srt[:10]:
    e = ents[k]
    P('    idx#%-3d %-26s off=0x%-9X stored=%-9d end=0x%X' % (k, e['name'][:26], e['off'],
                                                            e['stored'], e['off'] + e['stored']))
P('  物理顺序末 3:')
for k in srt[-3:]:
    e = ents[k]
    P('    idx#%-3d %-26s off=0x%-9X stored=%-9d end=0x%X' % (k, e['name'][:26], e['off'],
                                                            e['stored'], e['off'] + e['stored']))
maxend = max(e['off'] + e['stored'] for e in ents if e['off'])
P('  ★ 最大 end = 0x%X = %d ; 头声明 size = %d ; 容器内尾料 = %d'
  % (maxend, maxend, hdr[0], hdr[0] - maxend))
ge = [i for i, e in enumerate(ents) if e['off'] >= 0xB9120]
lt = [i for i, e in enumerate(ents) if 0 < e['off'] < 0xB9120]
P('  ★ off ≥ 0xB9120 的条目 = %d 个 (idx %d..%d)' % (len(ge), ge[0], ge[-1]))
P('  ★ off <  0xB9120 的条目 = %d 个' % len(lt))
P('  ★ off<0xB9120 但 end>0xB9120 的条目: %s'
  % [(i, ents[i]['name'], hex(ents[i]['off']), ents[i]['off'] + ents[i]['stored'])
     for i in lt if ents[i]['off'] + ents[i]['stored'] > 0xB9120])
P('  ★ off ≥ 0xB9120 里最小的 off = 0x%X' % min(ents[i]['off'] for i in ge))
# 对齐检查
P('  ★ off ≥ 0xB9120 的 off 是否全 16 对齐: %s'
  % all(ents[i]['off'] % 16 == 0 for i in ge))
P('  ★ off ≥ 0xB9120 的 off 是否全 4 对齐: %s'
  % all(ents[i]['off'] % 4 == 0 for i in ge))
P('  ★ stored=0 的条目数 = %d' % sum(1 for e in ents if e['stored'] == 0))

P('')
P('=' * 78)
P('[8] 新格位表 (slot 1504..1871) 与旧带重叠检查')
P('=' * 78)
old_bands = []
for (nm2, fld, rs) in faces:
    for r in rs:
        if r[3] in (452, 482):
            old_bands.append((r[2] + 4, r[3] + 2, r[4] + 4, r[5] + 2))
P('  旧带采样窗矩形 %d 个' % len(old_bands))
rows = {}
for slot in range(1504, 1871 + 1):
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    row = slot // 62
    rows.setdefault(row, []).append((slot, x, y))
for row in sorted(rows):
    xs = [x for _, x, _ in rows[row]]
    ys = {y for _, _, y in rows[row]}
    P('  row %-3d y=%-4d 格 %d 个 (slot %d..%d) 列 %d..%d'
      % (row, list(ys)[0], len(rows[row]), rows[row][0][0], rows[row][-1][0],
         min(xs) // 16, max(xs) // 16))
ov = 0
for slot in range(1504, 1871 + 1):
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    for (a, b, c, d) in old_bands:
        if x < c and a < x + 16 and y < d and b < y + 16:
            ov += 1
P('  ★ 新 368 格与旧带采样窗重叠的 texel = %d (期望 >0 ⇒ 必须搬带)' % ov)
P('  ★ 新格覆盖的 y 范围 = %d..%d ; 最大 y+16 = %d'
  % (min(tcslib.atlas_cell_xy_engine_view(s)[1] for s in range(1504, 1872)),
     max(tcslib.atlas_cell_xy_engine_view(s)[1] for s in range(1504, 1872)),
     max(tcslib.atlas_cell_xy_engine_view(s)[1] for s in range(1504, 1872)) + 16))
P('  ★ slot 1504..1871 的 lead 范围 = 0x%02X..0x%02X'
  % (tcslib.pair_from_slot(1504)[0], tcslib.pair_from_slot(1871)[0]))

iso.close()
with open(os.path.join(OUT, 'recon2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(buf) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'recon2.txt'))
