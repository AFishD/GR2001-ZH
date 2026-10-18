# -*- coding: utf-8 -*-
r"""pc_glyph_grab.py — 从 PC 版自带中文字库里取出 PS2 TTF 缺的那个字（先查 嘚 U+561A）

PC 侧（任务 d69bc993 已证）:
  gbtext.def = 1288×2B [lead,trail] GBK 码表，记录序 = 槽位
  GB{12,16,24}{00..04}.TGA = 18B TGA头 + 512×512×4 BGRA 页纹理
  寻址: perRow = 512/S ; perPage = perRow² ; page = slot/perPage ; row = cell/perRow ;
        col = cell%perRow ; X = col*S ; Y = row*S
本脚本: 查缺字在 gbtext.def 里的槽位 ⇒ 从 GB16 页里取出 16×16 位图 ⇒ 输出 4bpp 墨迹 + ASCII 预览
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
PC = os.path.join(REPO, 'third_party', 'orig', 'ghost_recon_pc')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(OUT, exist_ok=True)

# 找 gbtext.def 与 GB16 页
cands = []
for root, dirs, files in os.walk(PC):
    for fn in files:
        low = fn.lower()
        if low == 'gbtext.def' or (low.startswith('gb16') and low.endswith('.tga')):
            cands.append(os.path.join(root, fn))
gb = [c for c in cands if c.lower().endswith('.def')]
pages = sorted([c for c in cands if c.lower().endswith('.tga')])
print('gbtext.def: %s' % (gb[:1] or '(未找到)'))
print('GB16 页 %d 个: %s' % (len(pages), [os.path.basename(p) for p in pages]))

if not gb or not pages:
    print('✗ 素材不全，无法继续')
    sys.exit(1)

defb = open(gb[0], 'rb').read()
print('gbtext.def %d B ⇒ %d 个槽位' % (len(defb), len(defb) // 2))

targets = ['嘚']
for ch in targets:
    gbk = ch.encode('gbk')
    print()
    print('查字 %s (U+%04X) GBK = %s' % (ch, ord(ch), gbk.hex().upper()))
    slot = None
    for i in range(len(defb) // 2):
        if defb[i * 2] == gbk[0] and defb[i * 2 + 1] == gbk[1]:
            slot = i
            break
    if slot is None:
        print('  ✗ gbtext.def 里没有这个字')
        continue
    print('  ✓ 找到！槽位 = **%d**' % slot)
    S = 16
    perRow = 512 // S
    perPage = perRow * perRow
    page = slot // perPage
    cell = slot % perPage
    row, col = cell // perRow, cell % perRow
    X, Y = col * S, row * S
    print('  16px 寻址: page=%d row=%d col=%d ⇒ 像素 (X,Y)=(%d,%d)' % (page, row, col, X, Y))
    if page >= len(pages):
        print('  ✗ 没有对应的 GB16 页文件（只有 %d 页）' % len(pages))
        continue
    raw = open(pages[page], 'rb').read()
    hdr = raw[:18]
    w, h, bpp = struct.unpack_from('<HH', hdr, 12)[0], struct.unpack_from('<HH', hdr, 14)[0], hdr[16]
    print('  TGA 头: %dx%d %dbpp（数据从 18 起）' % (w, h, bpp))
    data = raw[18:]
    stride = w * 4
    px = []
    for y in range(S):
        rowpx = []
        for x in range(S):
            off = (Y + y) * stride + (X + x) * 4
            b, g, r, a = data[off], data[off + 1], data[off + 2], data[off + 3]
            rowpx.append(0 if a < 128 else (1 if (r + g + b) > 384 else 0))
        px.append(rowpx)
    ink = sum(sum(r) for r in px)
    print('  取到 16×16 位图，墨像素 %d / 256' % ink)
    print('  预览（# = 墨）:')
    for r in px:
        print('     ' + ''.join('#' if v else '.' for v in r))
    # 输出 4bpp（墨=0x0，底=0x1 —— 与 PS2 现役图集一致）
    out = bytearray(128)
    for y in range(16):
        for x in range(0, 16, 2):
            lo = px[y][x]
            hi = px[y][x + 1]
            out[(y * 16 + x) // 2] = lo | (hi << 4)
    fn = os.path.join(OUT, 'pc_glyph_%04X_4bpp.bin' % ord(ch))
    open(fn, 'wb').write(bytes(out))
    print('  → 已写出 %s (%d B, 4bpp, 墨=0x0/底=0x1)' % (fn, len(out)))
