# -*- coding: utf-8 -*-
r"""zx_w2048_recon.py — W=2048 探针的**只读**侦察: 把"要同步的 4 个地方"全部量化。

    python tools/re/toolbelt/zx_w2048_recon.py [iso]

产出: work/builds/GR_TEST_W2048/recon.json + 屏幕日志。
不写任何东西到 ISO。
"""
import io
import json
import os
import struct
import sys
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_TEST_W2048')
SEC = 2048
LOG = []
D = {}


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


iso = tcslib.Iso(ISO)
size = iso.size
P('=' * 78)
P('zx_w2048_recon.py  src = %s' % ISO)
P('  ISO 大小 = %d B = %d 扇区' % (size, size // SEC))
D['iso_path'] = ISO
D['iso_bytes'] = size
D['iso_sectors'] = size // SEC

# ─── [1] PVD / SVD / 根目录 ───
P('-' * 78)
P('[1] ISO9660 卷描述符 + 根目录')
pvd = iso.read(16 * SEC, SEC)
vol_le = struct.unpack_from('<I', pvd, 80)[0]
vol_be = struct.unpack_from('>I', pvd, 84)[0]
sysid = pvd[8:40].decode('latin-1').rstrip()
volid = pvd[40:72].decode('latin-1').rstrip()
P('  PVD type=%d id=%s sys=%s vol=%s' % (pvd[0], pvd[1:6].decode('latin-1'), sysid, volid))
P('  vol_space 小端=%d 大端=%d %s ; 文件扇区数=%d %s'
  % (vol_le, vol_be, '一致 ✓' if vol_le == vol_be else '不一致 ✗', size // SEC,
     '一致 ✓' if vol_le == size // SEC else '不一致 ✗'))
D['pvd'] = dict(vol_le=vol_le, vol_be=vol_be, sysid=sysid, volid=volid,
                vol_off_le=16 * SEC + 80, vol_off_be=16 * SEC + 84)
# 其它卷描述符
svds = []
lba = 17
while True:
    d = iso.read(lba * SEC, SEC)
    if not d or d[0] == 255:
        break
    if d[0] == 2:
        svds.append(dict(lba=lba, id=d[1:6].decode('latin-1'), esc=d[88:120].hex(),
                         vol_le=struct.unpack_from('<I', d, 80)[0],
                         vol_be=struct.unpack_from('>I', d, 84)[0]))
    lba += 1
P('  SVD: %s' % (svds or '无'))
D['svd'] = svds
root = pvd[156:156 + 34]
root_lba = struct.unpack_from('<I', root, 2)[0]
root_len = struct.unpack_from('<I', root, 10)[0]
P('  根目录 LBA=%d len=%d' % (root_lba, root_len))
D['root'] = dict(lba=root_lba, len=root_len)


def parse_dir(lba, length):
    d = iso.read(lba * SEC, length)
    out, i = [], 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(d):
                break
            continue
        rec = d[i:i + L]
        nl = rec[32]
        nm = rec[33:33 + nl].decode('latin-1')
        out.append(dict(off_in_dir=i, lba=struct.unpack_from('<I', rec, 2)[0],
                        len_le=struct.unpack_from('<I', rec, 10)[0],
                        len_be=struct.unpack_from('>I', rec, 14)[0],
                        flags=rec[25], name=nm, rec_len=L, abs=root_lba * SEC + i))
        i += L
    return out


ents = parse_dir(root_lba, root_len)
P('  根目录条目 %d 个:' % len(ents))
for e in sorted(ents, key=lambda x: x['lba']):
    P('    LBA=%-8d  %-14s size=%-12d %s  记录@ISO+0x%X'
      % (e['lba'], e['name'], e['len_le'], 'LE/BE %s' % ('✓' if e['len_le'] == e['len_be'] else '✗'),
         e['abs']))
D['root_ents'] = ents
menu = [e for e in ents if e['name'].upper().startswith('MENU')]
assert len(menu) == 1, menu
menu = menu[0]
P('  ★ MENU.IMG: LBA=%d len=%d (大端 %d %s) 记录@ISO 0x%X'
  % (menu['lba'], menu['len_le'], menu['len_be'],
     '✓' if menu['len_le'] == menu['len_be'] else '✗', menu['abs']))
P('    data length 小端字段@0x%X ; 大端字段@0x%X' % (menu['abs'] + 10, menu['abs'] + 14))
P('    MENU.IMG LBA = %d ; tcslib.MENU_LBA = %d %s'
  % (menu['lba'], zx_lib.MENU_LBA, '一致 ✓' if menu['lba'] == zx_lib.MENU_LBA else '✗'))
last_other = max((e['lba'] + (e['len_le'] + SEC - 1) // SEC for e in ents
                  if e is not menu), default=0)
P('    其它文件最大结束扇区 = %d ⇒ MENU.IMG %s'
  % (last_other, '确实在盘尾' if menu['lba'] >= last_other else '★ 后面还有文件'))
P('    MENU.IMG 可占扇区 = %d .. %d = %d 扇区 = %d B (MAX_MENU)'
  % (menu['lba'], vol_le - 1, vol_le - menu['lba'], (vol_le - menu['lba']) * SEC))
D['menu_rec'] = dict(abs=menu['abs'], lba=menu['lba'], len_le=menu['len_le'],
                     len_be=menu['len_be'], max_menu_bytes=(vol_le - menu['lba']) * SEC)

# ─── [2] MENU.IMG 容器 ───
P('-' * 78)
P('[2] MENU.IMG 内部')
hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
P('  头 12×u32 = %s' % [hex(x) for x in hdr['raw']])
P('  size=%d names_end=%d sector=%d tbl_end=0x%X names_start=0x%X data_start=0x%X hash_off=0x%X'
  % (hdr['size'], hdr['names_end'], hdr['sector'], hdr['tbl_end'],
     hdr['names_start'], hdr['data_start'], hdr['hash_off']))
P('  ★ 声明长度 %d ; ISO9660 目录记录长度 %d ⇒ %s'
  % (hdr['size'], menu['len_le'], '一致 ✓' if hdr['size'] == menu['len_le'] else '★ 不一致'))
P('  名字区 %d B sha=%s ; 4096 槽表 16,384 B sha=%s' % (len(names0), sha(names0), sha(hash0)))
D['menu_hdr'] = hdr

M = zx_lib.entries(iso, zx_lib.MENU_LBA)
P('  条目 %d 个' % len(M))
D['menu_nents'] = len(M)
idx_pak = [e['idx'] for e in M if e['name'] == 'COMMON.PAK'][0]
idx_ft = [e['idx'] for e in M if e['name'] == 'FONT.RES'][0]
e_pak, e_ft = M[idx_pak], M[idx_ft]
P('  COMMON.PAK #%d off=0x%X stored=%d real=%d' % (idx_pak, e_pak['off'], e_pak['stored'], e_pak['real']))
P('  FONT.RES   #%d off=0x%X stored=%d real=%d' % (idx_ft, e_ft['off'], e_ft['stored'], e_ft['real']))
P('  ⇒ PAK off+stored = 0x%X ; FONT.RES off = 0x%X (间隙 %d B)'
  % (e_pak['off'] + e_pak['stored'], e_ft['off'], e_ft['off'] - (e_pak['off'] + e_pak['stored'])))
D['e_pak'] = dict(idx=idx_pak, off=e_pak['off'], stored=e_pak['stored'], real=e_pak['real'])
D['e_ft'] = dict(idx=idx_ft, off=e_ft['off'], stored=e_ft['stored'], real=e_ft['real'])
last_end = max(e['off'] + e['stored'] for e in M)
who = [e['name'] for e in M if e['off'] + e['stored'] == last_end]
P('  ★ 最后条目 end = %d (%s) ; 声明长度 %d ⇒ 容器内尾料 %d B'
  % (last_end, who, hdr['size'], hdr['size'] - last_end))
tail = bytes(iso.mm[zx_lib.MENU_LBA * SEC + last_end: zx_lib.MENU_LBA * SEC + hdr['size']])
nz = [i for i in range(len(tail)) if tail[i]]
P('    尾料 [%d,%d) 非零字节 %d 个 %s' % (last_end, hdr['size'], len(nz),
                                     ('首个 @+%d = 0x%02X' % (nz[0], tail[nz[0]])) if nz else ''))
D['last_end'] = last_end
D['menu_tail'] = dict(beg=last_end, end=hdr['size'], n_nonzero=len(nz))
# 所有条目里 off >= FONT.RES off 的条数与最大 end
after = [e for e in M if e['off'] >= e_ft['off']]
P('  off >= FONT.RES.off 的条目 = %d 个 (其中 stored>0: %d)'
  % (len(after), sum(1 for e in after if e['stored'])))
D['menu_after_ft'] = len(after)
# 条目表里 off/stored 字段绝对位置
P('  条目表 @IMG+0x%X step %d ⇒ 条目 #i 的记录 @IMG+0x%X'
  % (zx_lib.TAB_OFF, zx_lib.TAB_STEP, zx_lib.TAB_OFF))
D['tab'] = dict(off=zx_lib.TAB_OFF, step=zx_lib.TAB_STEP)

# ─── [3] COMMON.PAK 记录链 ───
P('-' * 78)
P('[3] COMMON.PAK 记录链')
pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
P('  PAK %d B (stored %d real %d)' % (len(pak), e_pak['stored'], e_pak['real']))
recs = tcslib.parse_pak_records(pak)
p = 0
D['pak_recs'] = []
for (nm, psm, w, h, clut, px, pxoff) in recs:
    P('  rec @PAK+0x%-6X %-20s psm=0x%02X %dx%d clut=%d px_size=0x%X px@0x%X'
      % (p, nm, psm, w, h, clut, px, pxoff))
    P('       字段: psm@+0x%X w@+0x%X h@+0x%X clut@+0x%X px_size@+0x%X'
      % (0, 0, 0, 0, 0) if False else
      '       记录内字段偏移: psm=+0x%X w=+0x%X h=+0x%X clut=+0x%X px_size=+0x%X 容器=+0x%X'
      % (pxoff - 20 - clut - p, pxoff - 16 - clut - p, pxoff - 12 - clut - p,
         pxoff - 8 - clut - p, pxoff - p, pxoff - p))
    D['pak_recs'].append(dict(idx=len(D['pak_recs']), start=p, name=nm, psm=psm, w=w, h=h,
                              clut=clut, px_size=px, px_off=pxoff))
    p = pxoff + px
P('  记录链结束 @0x%X ; PAK 尾余 %d B ; 头 16 B @结束处 = %s'
  % (p, len(pak) - p, pak[p:p + 16].hex(' ')))
P('  结束哨兵区 @0x%X: type=0x%X (尾 4 B 无 nameLen 字段)'
  % (p, struct.unpack_from('<I', pak, p)[0]))
D['pak_recs_end'] = p

# ─── [4] new_font_revised 记录 + 容器 ───
P('-' * 78)
P('[4] new_font_revised 记录 + 像素容器 (GIF 封包流)')
r1 = D['pak_recs'][1]
R = r1['start']
P('  记录 @PAK+0x%X ; 容器 @PAK+0x%X ; px_size=0x%X' % (R, r1['px_off'], r1['px_size']))
for fld, off in (('psm', 0), ('w', 0), ('h', 0), ('clut_size', 0), ('px_size', 0)):
    pass
P('  ★ 关键字段 (记录内偏移 → 值 → 绝对 @PAK / @ISO):')
for lbl, roff in (('psm', r1['px_off'] - r1['start'] - 20 - r1['clut']),
                  ('w', r1['px_off'] - r1['start'] - 16 - r1['clut']),
                  ('h', r1['px_off'] - r1['start'] - 12 - r1['clut']),
                  ('clut_size', r1['px_off'] - r1['start'] - 8 - r1['clut']),
                  ('px_size', r1['px_off'] - r1['start'])):
    v = struct.unpack_from('<I', pak, R + roff)[0]
    P('    +0x%03X  %-9s = 0x%X (%d)   @PAK+0x%X  @ISO+0x%X'
      % (roff, lbl, v, v, R + roff, e_pak['iso_off'] + R + roff))
    D['field_' + lbl] = dict(rec_off=roff, value=v, abs_iso=e_pak['iso_off'] + R + roff)
ct = bytes(pak[r1['px_off']:r1['px_off'] + r1['px_size']])
segs = tcslib.atlas_container_segments(ct, r1['w'] // 2)
P('  atlas_container_segments(%d, stride %d) → %d 段' % (len(ct), r1['w'] // 2, len(segs or [])))
pref = []
for k, (row, doff, nb) in enumerate(segs):
    hx = ct[doff - 48:doff]
    w0, w1 = struct.unpack_from('<II', ct, doff - 48)
    a0, a1 = struct.unpack_from('<II', ct, doff - 32)
    a2, a3 = struct.unpack_from('<II', ct, doff - 24)
    i0, i1 = struct.unpack_from('<II', ct, doff - 16)
    P('   seg%d 首行=%-4d doff=0x%-6X nb=%-6d' % (k, row, doff, nb))
    P('     PT   tag: w0=0x%08X w1=0x%08X (nloop=%d eop=%d nreg=%d flg=%d)'
      % (w0, w1, w0 & 0x7FFF, (w0 >> 15) & 1, (((w1 >> 28) - 1) & 0xF) + 1, (w1 >> 26) & 3))
    P('     A+D  tag: data=0x%08X_%08X reg=0x%08X_%08X (regid=0x%X)'
      % (a1, a0, a3, a2, a3 & 0xFF))
    P('     IMG  tag: w0=0x%08X w1=0x%08X (nloop=%d eop=%d flg=%d)'
      % (i0, i1, i0 & 0x7FFF, (i0 >> 15) & 1, (i1 >> 26) & 3))
    P('     48B hex: %s' % hx.hex(' '))
    pref.append(dict(k=k, first_row=row, doff=doff, nb=nb, pt=(w0, w1), ad=(a0, a1, a2, a3),
                     img=(i0, i1), hex=hx.hex()))
D['segs'] = pref
tr = ct[r1['px_size'] - 16:]
P('  尾部 16 B = %s' % tr.hex(' '))
t0, t1 = struct.unpack_from('<II', ct, r1['px_size'] - 16)
P('    nloop=%d eop=%d flg=%d' % (t0 & 0x7FFF, (t0 >> 15) & 1, (t1 >> 26) & 3))
D['trailer'] = tr.hex()
P('  容器字节账: %d 段 × 48 + Σ数据 %d + 16 = %d == px_size %d %s'
  % (len(segs), sum(s[2] for s in segs), len(segs) * 48 + sum(s[2] for s in segs) + 16,
     r1['px_size'], '✓' if len(segs) * 48 + sum(s[2] for s in segs) + 16 == r1['px_size'] else '✗'))

# ─── [5] 计算 Δ 与新账 ───
P('-' * 78)
P('[5] W=2048 后的账')
W_OLD, W_NEW, H = 1024, 2048, 512
CT_OLD = 8 * (48 + 0x8000) + 16
CT_NEW = 16 * (48 + 0x8000) + 16
D['ct_old'] = CT_OLD
D['ct_new'] = CT_NEW
D['delta'] = CT_NEW - CT_OLD
P('  容器 %d → %d (Δ %+d) ; px_size 0x%X → 0x%X' % (CT_OLD, CT_NEW, CT_NEW - CT_OLD, 0x40010, 0x80010))
P('  新 W=%d h=%d @4bpp = %d B ; 16 段 × 0x8000 = %d B ✓'
  % (W_NEW, H, W_NEW * H // 2, 16 * 0x8000))
delta = CT_NEW - CT_OLD
new_pak_len = len(pak) + delta
new_last_end = last_end + delta
new_menu_need = new_last_end
new_menu_size = ((new_menu_need + SEC - 1) // SEC) * SEC
max_menu = (vol_le - menu['lba']) * SEC
P('  PAK %d → %d' % (len(pak), new_pak_len))
P('  MENU 条目最大 end %d → %d' % (last_end, new_last_end))
P('  扇区对齐新声明长度 = %d (%d 扇区)' % (new_menu_size, new_menu_size // SEC))
P('  ★ 现声明 %d ; 盘尾上限 MAX_MENU = %d ⇒ 需再延长 %d B = %d 扇区 (%.1f 扇区)'
  % (hdr['size'], max_menu, new_menu_size - hdr['size'], (new_menu_size - hdr['size']) // SEC,
     (new_menu_size - hdr['size']) / float(SEC)))
P('  ⇒ ISO 需从 %d 扇区长到 %d 扇区 (Δ %+d 扇区 = %+d B)'
  % (vol_le, menu['lba'] + new_menu_size // SEC, menu['lba'] + new_menu_size // SEC - vol_le,
     (menu['lba'] + new_menu_size // SEC - vol_le) * SEC))
D['new_pak_len'] = new_pak_len
D['new_last_end'] = new_last_end
D['new_menu_size'] = new_menu_size
D['max_menu'] = max_menu
D['new_vol_sectors'] = menu['lba'] + new_menu_size // SEC
D['new_iso_bytes'] = D['new_vol_sectors'] * SEC

os.makedirs(OUT, exist_ok=True)
with io.open(os.path.join(OUT, 'recon.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(dict(log=LOG, data=D), f, ensure_ascii=False, indent=1)
with io.open(os.path.join(OUT, 'recon.log'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(LOG) + '\n')
P('[out] %s' % os.path.join(OUT, 'recon.json'))
iso.close()
