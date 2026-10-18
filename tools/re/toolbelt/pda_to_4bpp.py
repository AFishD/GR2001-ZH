# -*- coding: utf-8 -*-
r"""pda_to_4bpp.py — 把 COMMON.PAK 里两张 256×256 PSMT8(pda-lcd-02 / pda_counterparts)
                     无损转成 PSMT4，回收 32,768 B/张（共 65,536 B）

依据（都是实测/既有事实）:
  · PAK 记录字段: {name}{mode}{psm}{w}{h}{clut_size}{clut...}{px_size}{px...}（解析器见 tools/iso_build 的 parse_pak_records）
  · 现役字形图集就是 **psm=0x14(PSMT4) + clut=0x410**，游戏正在跑它 ⇒ 该组合已被实机验证 ✓
  · PSMT8: 每字节 1 个 8 位调色板索引；PSMT4: 每字节 2 个像素（**偶 x 在低半字节** —— 见 docs/REPORT_atlas_artifact.md）
  · 转换前提: 该图用到的索引必须 < 16（否则非无损，本脚本会拒绝并报告）

输出: work/builds/GR_ZH98/temp/r82/ 下: pda_lcd_4bpp.bin / pda_cp_4bpp.bin / convert_report.txt
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
os.makedirs(OUT, exist_ok=True)

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = 776286
iso = tcslib.Iso(ISO)

# 1) 找 COMMON.PAK 条目
pak_entry = None
n = 0
while n < 2000:
    e = iso.img_entry(MENU_LBA, n)
    if e['name'].startswith('?'):
        break
    if 'COMMON' in e['name'].upper():
        pak_entry = e
        break
    n += 1
if not pak_entry:
    print('✗ 没找到 COMMON.PAK')
    sys.exit(1)
pak = iso.read(pak_entry['iso_off'], pak_entry['real'])
print('COMMON.PAK 条目 #%d  %s  stored=%d real=%d' % (n, pak_entry['name'], pak_entry['stored'], pak_entry['real']))

# 2) 解析记录（按已知布局）
recs = []
p = 0
for i in range(8):
    # {u32 flag}{u32 nl}{name}{8×u32 hdr}{clut_size B}{w*h px} —— 用实际字段顺序解析
    flag, nl = struct.unpack_from('<II', pak, p)
    if nl == 0 or nl > 64:
        break
    name = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1')
    q = p + 8 + nl
    hdr = struct.unpack_from('<8I', pak, q)
    psm, w, h = hdr[0], hdr[1], hdr[2]
    clut_size = hdr[3] if len(hdr) > 3 else 0
    q2 = q + 32
    clut = pak[q2:q2 + clut_size]
    q3 = q2 + clut_size
    px_size = struct.unpack_from('<I', pak, q3)[0]
    px_off = q3 + 4
    recs.append(dict(idx=i, name=name, psm=psm, w=w, h=h, clut_size=clut_size,
                     clut_off=q2, px_size=px_size, px_off=px_off,
                     hdr_off=q, rec_off=p, end=px_off + px_size))
    print('  #%d %-22s psm=0x%02X %dx%d clut=%d px=0x%X' % (i, name, psm, w, h, clut_size, px_size))
    p = px_off + px_size
    # 对齐到 4 字节
    while p % 4:
        p += 1

report = []
for r in recs:
    if r['psm'] != 0x13 or r['w'] != 256 or r['h'] != 256:
        continue
    px = pak[r['px_off']:r['px_off'] + r['px_size']]
    nb = r['w'] * r['h']
    if len(px) < nb:
        report.append('%s: 像素数据不足 (%d < %d)' % (r['name'], len(px), nb))
        continue
    idx = list(px[:nb])
    mx = max(idx)
    hist = {}
    for v in idx:
        hist[v] = hist.get(v, 0) + 1
    line = ('%s: 256x256 PSMT8, 用到 %d 种索引, 最大索引 %d ⇒ %s'
            % (r['name'], len(hist), mx, '可无损转 4bpp ✓' if mx < 16 else '**索引 ≥16，非无损，拒绝转换** ✗'))
    print('  ' + line)
    report.append(line)
    if mx >= 16:
        continue
    # 3) 打包 4bpp: 偶 x 在低半字节
    out = bytearray(nb // 2)
    for y in range(r['h']):
        row = y * r['w']
        for x in range(0, r['w'], 2):
            lo = idx[row + x] & 0xF
            hi = idx[row + x + 1] & 0xF
            out[(row + x) // 2] = lo | (hi << 4)
    fn = os.path.join(OUT, r['name'].replace('-', '_').replace(' ', '_') + '_4bpp.bin')
    open(fn, 'wb').write(bytes(out))
    print('    → 写出 %s  (%d B, 原 %d B, 回收 %d B)'
          % (os.path.basename(fn), len(out), r['px_size'], r['px_size'] - len(out)))
    report.append('  → %s: %d B (原 %d B, 回收 %d B)' % (os.path.basename(fn), len(out), r['px_size'], r['px_size'] - len(out)))

open(os.path.join(OUT, 'convert_report.txt'), 'w', encoding='utf-8').write('\n'.join(report) + '\n')
print()
print('报告: %s' % os.path.join(OUT, 'convert_report.txt'))
iso.close()
