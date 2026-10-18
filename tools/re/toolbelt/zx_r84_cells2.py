# -*- coding: utf-8 -*-
r"""zx_r84_cells2.py — round84：**格位需求核算（修正版）**（只读）

★ 修正：charset `codes` 的值 = **字节码**，记录索引 = 字节码 − 0x20（face[+0x20]=0x20）。
  所以 键/练/用 的「原单字节记录」是 **idx = code − 0x20**，不是 code。
  本轮把「每个单字节码实际引用哪条记录」逐条算清。

产出 work/builds/GR_ZH98/temp/r84/cells2.txt
"""
import io
import os
import sys
import json
import csv

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np        # noqa: E402
import tcslib             # noqa: E402
import zx_lib             # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r84')
os.makedirs(OUT, exist_ok=True)
W, H = 1024, 512
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
names = []
for i in range(2000):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
pak_e = iso.img_entry(tcslib.MENU_LBA, names.index('COMMON.PAK'))
pak = bytes(iso.read(pak_e['iso_off'], pak_e['stored']))
nm, psm, aw, ah, clut, pxs, PX = tcslib.parse_pak_records(pak)[1]
img, cov = zx_lib.decode_engine(pak[PX:PX + pxs], W, H)
ft_e = iso.img_entry(tcslib.MENU_LBA, names.index('FONT.RES'))
exp = b''.join(s[0] for s in tcslib.lzo_subs(bytes(iso.read(ft_e['iso_off'], ft_e['stored']))))
he, faces = tcslib.parse_ft_faces(exp)
iso.close()

cs = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))
codes = cs['codes']
pair_of = cs['pair_of']
recs = {f[0]: f[2] for f in faces}

P('图集 %dx%d = %d texel = **%d 个 16x16 格位**' % (W, H, W * H, W * H // 256))
P('charset: codes=%d 个单字节码 ; pair_of=%d 个对偶码' % (len(codes), len(pair_of)))
P('')

# ── 单字节码 -> 记录索引（idx = code - 0x20）──
sb = {}
for ch, code in sorted(codes.items(), key=lambda kv: kv[1]):
    idx = code - 0x20
    r = recs['default'][idx] if 0 <= idx < len(recs['default']) else None
    sb[ch] = (code, idx, r)
P('单字节码 %d 个 -> 记录 idx %d..%d' % (len(sb), min(v[1] for v in sb.values()),
                                        max(v[1] for v in sb.values())))
if 96 in [v[1] for v in sb.values()]:
    P('  ★ 其中 idx=96 是否被引用: %s' % ('是' if 96 in [v[1] for v in sb.values()] else '否'))

# ASCII 段：idx 0..95 = 字节 0x20..0x7F，由引擎硬编码使用（precision ASCII）
ascii_rects = set()
for idx in range(96):
    b0, b1, u0, v0, u1, v1 = recs['default'][idx]
    if u1 > u0:
        ascii_rects.add((u0, v0, u1, v1))
P('ASCII 段记录 idx 0..95 : 唯一矩形 %d 个' % len(ascii_rects))

# 单字节码用到的记录（idx >= 96）+ 键/练/用 的旧记录
used_idx = sorted({v[1] for v in sb.values() if v[1] >= 96})
used_rects = {}
for idx in used_idx:
    b0, b1, u0, v0, u1, v1 = recs['default'][idx]
    if u1 > u0:
        used_rects.setdefault((u0, v0, u1, v1), []).append(idx)
P('单字节码引用的记录(idx>=96): %d 个 idx -> %d 个唯一矩形' % (len(used_idx), len(used_rects)))
legacy = [(c, v) for c, v in sb.items() if c in ('键', '练', '用')]
P('键/练/用 原单字节映射: %s' % [(c, '0x%02X' % v[0], v[1]) for c, v in legacy])

# 空白矩形
def hasink(r):
    return bool(img[r[1]:r[3], r[0]:r[2]].any())


live_used = {k: v for k, v in used_rects.items() if hasink(k)}
narrow = [k for k in live_used if k[2] - k[0] <= 8]
wide = [k for k in live_used if k[2] - k[0] > 8]
P('单字节字形记录(有墨): %d 条 -> 窄(<=8px) %d / 宽 %d' % (len(live_used), len(narrow), len(wide)))

# 去重：live_used 里有多少矩形与 ASCII 段共用
share = [k for k in live_used if k in ascii_rects]
P('与 ASCII 段共用矩形的: %d 个' % len(share))

P('')
P('=' * 78)
P('★ 图集格位需求核算（修正 idx 后）')
n_rec_cells = len(wide) + (len(narrow) + 1) // 2
P('  ① 对偶码字形（网格）        = 1736 格位')
P('  ② ASCII 段记录（idx 0..95） = %d 格位（%d 个唯一矩形）' % (len(ascii_rects), len(ascii_rects)))
P('  ③ 单字节汉字记录（idx>=96） = %d 格位（%d 条有墨：窄 %d 成对共格 -> %d，宽 %d）'
  % (n_rec_cells, len(live_used), len(narrow), (len(narrow) + 1) // 2, len(wide)))
P('  ④ 364 个新字                = 364 格位')
need = 1736 + len(ascii_rects) + n_rec_cells + 364
P('  ' + '-' * 60)
P('  合计 = 1736 + %d + %d + 364 = **%d 格位**' % (len(ascii_rects), n_rec_cells, need))
P('  图集 = **2048 格位**  ⇒  ★★ 缺口 **%d 格位** (超 %.1f%%)'
  % (need - 2048, 100.0 * (need - 2048) / 2048.0))
P('')
P('  ⇒ **364 个新字在 1024x512 图集里放不下**（与寻址/代码无关，是纯面积事实）')
P('  ⇒ 硬上限：2048 − %d(ASCII) − %d(记录) = **%d 格位**可给字形'
  % (len(ascii_rects), n_rec_cells, 2048 - len(ascii_rects) - n_rec_cells))
P('  ⇒ 相对现役 1736 ⇒ **最多再加 %d 个新字**（要求布局零浪费）'
  % (2048 - len(ascii_rects) - n_rec_cells - 1736))

P('')
P('  敏感度：')
for tag, c in (('ASCII 8px 保持 + 记录原样', n_rec_cells),
               ('ASCII + 所有记录都压到 8px 宽', (204 + 1) // 2)):
    P('     %-34s 记录占 %3d 格 -> 最多再加 %d 个'
      % (tag, c, 2048 - 96 - c - 1736))

with io.open(os.path.join(OUT, 'cells2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'cells2.txt'))
