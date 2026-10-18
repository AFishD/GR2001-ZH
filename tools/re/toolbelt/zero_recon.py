# -*- coding: utf-8 -*-
r"""zero_recon.py — 「零缺字成品盘」A 阶段只读侦察

只读 GR_ZH113b.iso + 仓库数据，输出:
  1. 现役字符集规模 (charset_compiled_zh16.json)
  2. 容器定位 (MENU.IMG / GR.IMG / COMMON.PAK) + 条目名
  3. FONT.RES 解析: 贴图名字符串 + 3 个 face 的 14 字段 + nrec + 记录表指纹
  4. 图集所在容器与记录 (new_font_revised)

产物 → work/builds/GR_ZH98/temp/r81/recon.txt
"""
import json
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT_DIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT_DIR, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
LS = []


def say(s=''):
    print(s)
    LS.append(s)


# ───────────────────────── 1. 字符集 ─────────────────────────
say('=' * 78)
say('[1] 现役字符集 tools/font_pipeline/data/charset_compiled_zh16.json')
say('=' * 78)
CSP = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
cs_raw = json.load(open(CSP, encoding='utf-8'))
say('  顶层键: %s' % list(cs_raw.keys()))
singles = {k: int(v) for k, v in cs_raw['codes'].items()}
pair_of = {k: tuple(v) for k, v in cs_raw['pair_of'].items()}
say('  单字节码位 codes: %d' % len(singles))
say('  对偶码位   pair_of: %d' % len(pair_of))
leads = sorted({v[0] for v in pair_of.values()})
say('  对偶 lead 字节: %d 个  %s' % (len(leads), ' '.join('%02X' % x for x in leads)))
say('  对偶 slot 范围: %d .. %d' % (min((l - 0xA1) * 94 + (t - 0xA1) for l, t in pair_of.values()),
                                    max((l - 0xA1) * 94 + (t - 0xA1) for l, t in pair_of.values())))
say('  单字节码范围: %s' % (' '.join('%02X' % v for v in sorted(singles.values()))))
sing_dup = len(singles.values()) - len(set(singles.values()))
pair_dup = len(pair_of.values()) - len(set(pair_of.values()))
say('  重复检查: single 重复 %d, pair 重复 %d' % (sing_dup, pair_dup))

# ───────────────────────── 2. ISO 容器 ─────────────────────────
say()
say('=' * 78)
say('[2] ISO 容器定位 (%s)' % os.path.basename(ISO))
say('=' * 78)
iso = tcslib.Iso(ISO)
say('  ISO 大小 %d B (%.3f GB)' % (iso.size, iso.size / 2 ** 30))

# 根目录里找 .IMG / .PAK
def iso9660_dir(lba, length):
    """读 ISO9660 目录记录 → {NAME: (lba, len, isdir)}"""
    d = iso.read(lba * 2048, length)
    out = {}
    i = 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i += 1
            continue
        rec = d[i:i + L]
        e_lba = struct.unpack_from('<I', rec, 2)[0]
        e_len = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        nl = rec[32]
        nm = rec[33:33 + nl].decode('ascii', 'replace')
        out[nm] = (e_lba, e_len, flags)
        i += L
    return out


ROOT = iso9660_dir(261, 384)          # 根目录 (LBA 261 由 tools/re/toolbelt/iso_ls.py 实测)
say('  根目录条目 %d 个: %s' % (len(ROOT), ' '.join(sorted(ROOT))))
CONTAINERS = {}
for base_ext, want in (('MENU.IMG', 'MENU.IMG;1'), ('GR.IMG', 'GR.IMG;1'),
                       ('COMMON.PAK', 'COMMON.PAK;1')):
    e = ROOT.get(want)
    if e:
        CONTAINERS[base_ext] = dict(lba=e[0], size=e[1])
        say('  %-12s LBA=%-8d size=%-12d (ISO9660 目录记录)' % (base_ext, e[0], e[1]))
    else:
        say('  %-12s ✗ 根目录里没有 %s' % (base_ext, want))

for k, v in CONTAINERS.items():
    base = v['lba'] * 2048
    hdr = struct.unpack_from('<5I', iso.mm, base)
    cnt = (hdr[3] - 0x830) // 48
    say('  %-12s @0x%X  头[0]=%d 名字末=%d 扇区=%d 表末=0x%X 名字起=0x%X  条目=%d'
        % (k, base, hdr[0], hdr[1], hdr[2], hdr[3], hdr[4], cnt))


def img_entries(lba, size):
    base = lba * 2048
    tbl_end = struct.unpack_from('<I', iso.mm, base + 0x0C)[0]
    names_start = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    names_end = struct.unpack_from('<I', iso.mm, base + 0x04)[0]
    cnt = (tbl_end - 0x830) // 48
    names = [x.decode('latin-1') for x in
             bytes(iso.mm[base + names_start:base + names_end]).split(b'\x00') if x]
    ents = []
    for i in range(cnt):
        r = struct.unpack_from('<12I', iso.mm, base + 0x830 + 48 * i)
        ents.append(dict(idx=i, stored=r[6], real=r[7], off=r[8],
                         name=names[i] if i < len(names) else '?%d' % i, raw=list(r)))
    return dict(base=base, tbl_end=tbl_end, names_start=names_start, names_end=names_end,
                cnt=cnt, names=names, ents=ents)


# ───────────────────────── 3. FONT.RES ─────────────────────────
say()
say('=' * 78)
say('[3] FONT.RES 解析 (MENU.IMG 内)')
say('=' * 78)
men = img_entries(CONTAINERS['MENU.IMG']['lba'], CONTAINERS['MENU.IMG']['size'])
say('  MENU.IMG 条目数 %d; 名字区 [0x%X,0x%X) len=%d'
    % (men['cnt'], men['names_start'], men['names_end'], men['names_end'] - men['names_start']))
for e in men['ents']:
    if e['idx'] < 12 or 'FONT' in e['name'].upper() or 'font' in e['name']:
        say('    #%-4d %-30r stored=%-8d real=%-8d off=0x%X'
            % (e['idx'], e['name'], e['stored'], e['real'], e['off']))
font_ent = [e for e in men['ents'] if e['name'].upper().startswith('FONT.RES')]
assert len(font_ent) == 1, [e['name'] for e in font_ent]
FE = font_ent[0]
say('  ★ FONT.RES = MENU.IMG 条目 #%d off=0x%X stored=%d real=%d (ISO 0x%X)'
    % (FE['idx'], FE['off'], FE['stored'], FE['real'], men['base'] + FE['off']))
slot = iso.read(men['base'] + FE['off'], FE['stored'])
say('  槽前 96 字节: %s' % slot[:96].hex(' '))
open(os.path.join(OUT_DIR, 'font_res_slot.bin'), 'wb').write(slot)

sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import decode_entry  # noqa: E402
ft, stats = decode_entry(slot)
say('  解出 %d B (stats=%s)' % (len(ft), stats))
open(os.path.join(OUT_DIR, 'font_res_expanded.bin'), 'wb').write(ft)

p, faces = tcslib.parse_ft_faces(ft) if hasattr(tcslib, 'parse_ft_faces') else (None, None)
if faces is None:
    raise SystemExit('tcslib.parse_ft_faces 不可用')
say('  尾部 styles 起点 0x%X, 尾长 %d B' % (p, len(ft) - p))
for nm, fld, recs in faces:
    say('  face %-8r fld=%s' % (nm, fld))
    say('        nrec = fld[4]*fld[5] = %d*%d = %d ; fld[1]=%d fld[2]=%d fld[3]=%d fld[6]=%d'
        % (fld[4], fld[5], fld[4] * fld[5], fld[1], fld[2], fld[3], fld[6]))
    say('        记录[0]=%s 记录[1]=%s 记录[0x20-0x20]=%s' % (recs[0], recs[1], recs[0x20 - 0x20]))
    nz = sum(1 for r in recs if r != recs[0])
    say('        与 rec[0] 不同的记录数 = %d' % nz)

# 贴图名
name_off = ft.index(b'\x00') - 22 if False else None
# 名字 = 头 4 字节之后的 Latin-1 串；按报告在 +0xD
say('  +0x0D 起的字符串: %r' % ft[0x0D:0x0D + 32].split(b'\x00')[0])
say('  +0x00..0x0C: %s' % ft[:0x0D].hex(' '))
tname = ft[0x0D:0x0D + 32].split(b'\x00')[0].decode('latin-1')
abs_off = men['base'] + FE['off'] + 0x0D
say('  ★ 贴图名 %r 长度 %d ; ISO 绝对偏移 0x%X' % (tname, len(tname), abs_off))
say('  原地 23 字节: %s' % iso.read(abs_off, 23).hex(' '))
say('  之后 12 字节: %s' % iso.read(abs_off + 23, 12).hex(' '))

# ───────────────────────── 4. 图集在哪 ─────────────────────────
say()
say('=' * 78)
say('[4] 图集条目 %r 在哪个容器' % tname)
say('=' * 78)
for k in ('MENU.IMG', 'GR.IMG', 'COMMON.PAK'):
    if k not in CONTAINERS:
        continue
    v = CONTAINERS[k]
    if k == 'COMMON.PAK':
        continue
    info = img_entries(v['lba'], v['size'])
    found = [e for e in info['ents'] if e['name'].lower() == tname.lower()
             or e['name'].lower().startswith(tname.lower())]
    say('  %-12s: %d 条匹配 %s' % (k, len(found), [(e['idx'], e['name'], e['stored'], e['real'], hex(e['off'])) for e in found]))

# COMMON.PAK: walk RSB 记录
cp = CONTAINERS.get('COMMON.PAK')
if cp:
    base = cp['lba'] * 2048
    say('  COMMON.PAK @0x%X 前 32 字节: %s' % (base, iso.read(base, 32).hex(' ')))
    # PAK walk: {u32 mode}{u32 nl}{name}{psm,w,h,clut}{px_size}{px}
    pak = iso.read(base, cp['size'])
    q = 0
    ents = []
    while q + 8 <= len(pak):
        mode, nl = struct.unpack_from('<II', pak, q)
        if nl < 1 or nl > 64 or q + 8 + nl > len(pak):
            break
        nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        r = q + 8 + nl
        psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
        r2 = r + 16 + clut
        px = struct.unpack_from('<I', pak, r2)[0]
        ents.append(dict(off=q, name=nm, psm=psm, w=w, h=h, clut=clut, px=px,
                         px_off=r2 + 4, end=r2 + 4 + px))
        q = r2 + 4 + px
        if q == len(pak):
            break
    say('  COMMON.PAK walk %d 条目:' % len(ents))
    for e in ents:
        mark = ' ★' if e['name'] == tname else ''
        say('     @0x%06X %-24r psm=0x%02X %dx%d clut=0x%X px=0x%X end=0x%X%s'
            % (e['off'], e['name'], e['psm'], e['w'], e['h'], e['clut'], e['px'], e['end'], mark))

iso.close()
open(os.path.join(OUT_DIR, 'recon.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
print('\n[OUT] %s' % os.path.join(OUT_DIR, 'recon.txt'))
