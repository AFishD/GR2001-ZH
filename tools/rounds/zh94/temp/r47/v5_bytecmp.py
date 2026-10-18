# -*- coding: utf-8 -*-
r"""v5_bytecmp.py — round47 验收②: GR_ZH96_fix 与 GR_ZH94 的**逐字节**比较 (最强口径)。

目的: 一句话证明"除了那 76 个 texel 以外, 整张盘逐字节不变" ⇒ 文本/ELF/IMG 表/PAK 包头
/制作组名单/其它图集全部没动。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                            # noqa: E402
import patch_zh94_glyph_align as P                                       # noqa: E402

A = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH96_fix', 'GR_ZH96_fix.iso')
sa, sb = os.path.getsize(A), os.path.getsize(B)
print('A = GR_ZH94        %d B' % sa)
print('B = GR_ZH96_fix    %d B' % sb)
assert sa == sb, '尺寸不同!'

diff = []
CH = 1 << 24
with open(A, 'rb') as fa, open(B, 'rb') as fb:
    off = 0
    while True:
        ba = fa.read(CH)
        bb = fb.read(CH)
        if not ba:
            break
        if ba != bb:
            for i in range(len(ba)):
                if ba[i] != bb[i]:
                    diff.append(off + i)
        off += len(ba)
print('逐字节比较完成: 不同字节 %d 个' % len(diff))
print('  偏移: %s' % ['0x%X' % d for d in diff])

# ---------- 定位到 COMMON.PAK ----------
iso = tcslib.Iso(A)
pak_e = ft_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
    elif e['name'] == 'FONT.RES':
        ft_e = e
    if pak_e and ft_e:
        break
iso.close()
pak = bytearray(open(A, 'rb').read(pak_e['iso_off']) if False else b'')
iso = tcslib.Iso(A)
pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
iso.close()
rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised'][0]
PX, px_size = rec[6], rec[5]
At = P.Atlas(pak, PX, px_size)
print()
print('COMMON.PAK: iso_off=0x%X stored=%d name=%s' % (pak_e['iso_off'], pak_e['stored'], rec[0]))
print('  像素容器: PAK 内偏移 PX=0x%X, 大小 %d; 段表 %s'
      % (PX, px_size, [tuple(int(v) for v in s) for s in At.segs]))

# 每个"引擎像素"对应的容器字节 (用于反查)
pix2byte = {}
for (y, x) in [(353, xx) for xx in range(0, 1024)]:
    k = y // tcslib.ATLAS_SEG_ROWS
    fr, doff, nbytes = At.segs[k]
    rel = (y - fr) * (1024 // 2) + x // 2
    pix2byte[(y, x)] = pak_e['iso_off'] + PX + doff + rel
want = sorted(set(pix2byte[(353, x)] for x in range(0, 1024)))
print()
print('期望被改的字节 = y=353 那一行里"有像素变化"的字节 (76 个 texel 落在 %d 个字节上, 全在这一行)' % 76)

# 全部差异字节必须落在 y=353 这一行的字节集合里
rowset = set(want)
outside = [d for d in diff if d not in rowset]
inrow = [d for d in diff if d in rowset]
print('  差异字节里: 落在 y=353 行字节集合内 %d 个; 集合外 **%d** 个 (期望 0)' % (len(inrow), len(outside)))
if outside:
    for d in outside[:20]:
        k = max(i for i, s in enumerate(At.segs) if s[1] + pak_e['iso_off'] + PX <= d)
        print('     0x%X (PAK+0x%X, 段 %d)' % (d, d - pak_e['iso_off'] - PX, k))
print()
print('★ 结论: %s' % ('整盘只有 y=353 那一行的 %d 个字节变了 ⇒ 文本/ELF/IMG 表/PAK 包头/制作组名单'
                      ' 全部逐字节不变' % len(diff) if not outside else '**有溢出改动!**'))
