# -*- coding: utf-8 -*-
r"""recon.py — round54 搬运前侦察: 84 条占位记录的**逐 face** 真相 + 目标空区的干净度。

回答 7 个问题 (全部只读):
  ① 3 个 face 的 fld14 / 记录条数 / 非空矩形数;
  ② 84 个占位码在 3 个 face 里各自的矩形 —— 是否一致? 尺寸是否一致?
  ③ 88 个"被活字形占着"的格子: 每个格子被**哪些 face 的哪些记录**压着 (含非活记录)?
  ④ 目标空区 y=194..241 里: 有没有**任何 face 的任何记录矩形**? (必须 0)
  ⑤ 空区墨量 (必须 0)、可用 16x16 格数 (必须 >= 84)
  ⑥ 8 个"其实不是单字节汉字"的码 (0x7B/0x7D/0xE7/0xF1) 在 3 face 里的矩形
  ⑦ 若清空 88 格后再分类: 88 格会变成 free_blank 还是 free_ft?
     (= 是否有**别的**记录矩形压在这些格上 ⇒ 压着就当不成"可用格")
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                        # noqa: E402
import tcslib                                                # noqa: E402
from patch_zh94_glyph_align import Atlas                     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH103', 'GR_ZH103.iso')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FREE_Y0, FREE_Y1 = 194, 242                                  # 目标空区 (半开区间)
KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}

w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
ink = A.eng
cs = json.load(io.open(CHARSET, encoding='utf-8'))
code2ch = {int(v): k for k, v in cs['codes'].items()}
print('图集 %dx%d psm=0x%02X 墨 %d px' % (W, H, ad['psm'], int(ink.sum())))
print()
print('=' * 78)
print('① 3 个 face 的结构')
print('=' * 78)
for nm, fld, rs in faces:
    nz = [(i + 0x20, r) for i, r in enumerate(rs)
          if r[2] < r[4] and r[3] < r[5]]
    print('  face %-8s fld14=%s' % (nm, fld))
    print('        记录 %d 条, 非空矩形 %d 条' % (len(rs), len(nz)))

# 每个 face 的 code → rect
face_rect = {}
for nm, fld, rs in faces:
    face_rect[nm] = {}
    for i, r in enumerate(rs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            face_rect[nm][i + 0x20] = (u0, v0, u1, v1)

NAME = {0x7B: '箭头{', 0x7D: '箭头}', 0xE7: 'ç', 0xF1: 'ñ'}


def nm_of(c):
    if c in NAME:
        return NAME[c]
    ch = code2ch.get(c)
    return ch if ch else (chr(c) if 0x20 <= c < 0x7F else '?')


print()
print('=' * 78)
print('② 84 个占位码在 3 个 face 里的矩形')
print('=' * 78)
targets = sorted(set(face_rect['large']))
# 只保留"落在 88 格里的"那些 (即 large 面里 u0%16==0 且 16 宽, 或者 4 条小矩形)
GOLD = []
for c in targets:
    u0, v0, u1, v1 = face_rect['large'][c]
    if not (0xAF <= c <= 0xFE or c in KEEP_HARD):
        continue
    # 只挑出"solid 活字形" (与侦察脚本同一判据, 后面再筛)
    GOLD.append(c)
print('  large 面 0xAF..0xFE ∪ {0x7B,0x7D} 的非空记录: %d 条' % len(GOLD))

mis = []
for c in GOLD:
    rs = {nm: face_rect[nm].get(c) for nm in face_rect}
    uniq = set(v for v in rs.values() if v is not None)
    if len(uniq) > 1 or any(v is None for v in rs.values()):
        mis.append((c, rs))
print('  其中"3 个 face 矩形不完全一致"的: %d 条' % len(mis))
for c, rs in mis[:20]:
    print('    0x%02X %-3s %s' % (c, nm_of(c), {k: v for k, v in rs.items()}))
print('  抽样 (前 6 条 + 4 条小矩形):')
for c in list(GOLD[:3]) + [0x7B, 0x7D, 0xE7, 0xF1] + list(GOLD[-3:]):
    if c not in face_rect['large']:
        continue
    rs = {nm: face_rect[nm].get(c) for nm in face_rect}
    print('    0x%02X %-3s %s' % (c, nm_of(c),
                                  ' '.join('%s=%s' % (k[:3], v) for k, v in rs.items())))

print()
print('=' * 78)
print('③ 88 个格子: 被哪些 face 的哪些记录压着')
print('=' * 78)
slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        slot_of[tcslib.pair_slot(b1, b2)] = ch
occ = {}
tdir = os.path.join(os.path.dirname(ISO), 'text')
for fn in os.listdir(tdir):
    if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
        import csv
        with io.open(os.path.join(tdir, fn), encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                for ch in (row.get('text_edited') or ''):
                    occ[ch] = occ.get(ch, 0) + 1


def is_live(code):
    if code in KEEP_HARD or 0x20 <= code <= 0x7E:
        return True
    if code in code2ch:
        return occ.get(code2ch[code], 0) > 0
    return False


# 所有 face 的矩形叠加 (认格用)
any_rect = np.zeros((H, W), dtype=bool)
owner = {}          # (face, code) → rect
for nm, rs in face_rect.items():
    for c, (u0, v0, u1, v1) in rs.items():
        any_rect[v0:v1, u0:u1] = True
        owner[(nm, c)] = (u0, v0, u1, v1)

# large 面的活矩形 (= font_cell_map 的口径)
live_large = np.zeros((H, W), dtype=bool)
for c, (u0, v0, u1, v1) in face_rect['large'].items():
    if is_live(c):
        live_large[v0:v1, u0:u1] = True

held = {}
for slot in range(1504):
    if slot in slot_of:
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    cell = ink[y:y + 16, x:x + 16]
    n = int(cell.sum())
    if n == 0:
        continue
    if int((cell & live_large[y:y + 16, x:x + 16]).sum()) != n:
        continue
    held[slot] = (x, y, n)
print('  88 格 (large 口径): %d 个' % len(held))

per_code = {}
multi_face = 0
other_hit = {}
for slot, (x, y, n) in sorted(held.items()):
    hits = [(nm, c, r) for (nm, c), r in owner.items()
            if x < r[2] and x + 16 > r[0] and y < r[3] and y + 16 > r[1]]
    codes = sorted(set(c for _nm, c, _r in hits))
    if len(codes) != 1:
        print('    !! slot %-4d (%d,%d) 被 %d 个不同码压着: %s'
              % (slot, x, y, len(codes), ' '.join('0x%02X' % c for c in codes)))
    for _nm, c, _r in hits:
        per_code.setdefault(c, []).append(slot)
        if _nm != 'large':
            multi_face += 1
    # 非本格的其它记录 (face/码不同) 也要看清
    for nm, c, r in hits:
        if r != face_rect['large'].get(c):
            other_hit.setdefault((nm, c), []).append((slot, r))
print('  88 格里出现的 (face≠large) 记录命中次数: %d' % multi_face)
print('  88 格里出现的"同一码但 face 矩形不同"的记录: %d 组' % len(other_hit))
for k, v in list(other_hit.items())[:10]:
    print('    %s %s → %d 格, 例 %s' % (k[0], '0x%02X' % k[1], len(v), v[0]))
print()
print('  按码统计 (格数):')
for c, ss in sorted(per_code.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    r = face_rect['large'].get(c)
    print('    0x%02X %-3s large=%s 尺寸 %s 占 %d 格'
          % (c, nm_of(c), r, (r[2] - r[0], r[3] - r[1]) if r else None, len(ss)))
print('  码数 %d, 格数合计 %d' % (len(per_code), sum(len(v) for v in per_code.values())))

print()
print('=' * 78)
print('④ 目标空区 y=%d..%d 里有没有记录矩形' % (FREE_Y0, FREE_Y1 - 1))
print('=' * 78)
n_hit = 0
for (nm, c), (u0, v0, u1, v1) in sorted(owner.items()):
    if v0 < FREE_Y1 and v1 > FREE_Y0:
        n_hit += 1
        print('    !! %s 0x%02X = (%d,%d,%d,%d)' % (nm, c, u0, v0, u1, v1))
print('  命中 %d 条 (必须 0)' % n_hit)
blk = ink[FREE_Y0:FREE_Y1, :]
print('  空区墨 %d px (必须 0)' % int(blk.sum()))
clean = 0
for y0 in range(FREE_Y0, FREE_Y1 - 15, 16):
    for x0 in range(0, W - 15, 16):
        if not blk[y0 - FREE_Y0:y0 - FREE_Y0 + 16, x0:x0 + 16].any() \
           and not any_rect[y0:y0 + 16, x0:x0 + 16].any():
            clean += 1
print('  干净 16x16 格 (无墨且不被任何 face 的记录压): %d' % clean)

print()
print('=' * 78)
print('⑤ 清空 88 格以后: 这些格会被判成什么? (free_blank 还是 free_ft)')
print('=' * 78)
target_codes = set(per_code)
bad = []
for slot, (x, y, n) in sorted(held.items()):
    left = [(nm, c, r) for (nm, c), r in owner.items()
            if x < r[2] and x + 16 > r[0] and y < r[3] and y + 16 > r[1]]
    after = [(nm, c, r) for nm, c, r in left if c not in target_codes]
    if after:
        bad.append((slot, x, y, after))
print('  清空后仍被**别的**记录矩形压着的格: %d 个' % len(bad))
for slot, x, y, after in bad[:20]:
    print('    slot %-4d (%d,%d): %s' % (slot, x, y,
          ' '.join('%s:0x%02X%s' % (nm, c, r) for nm, c, r in after)))
# 还要检查: 那些"完全落在格内但没有墨"的矩形 (空框, 如空格/未用码) 压着的格
print()
print('  反向检查: 目标 88 格里**完全没有墨但被记录压着**的情况 (分类为 free_ft 的)')
n_blank_ft = 0
for slot in range(1504):
    if slot in slot_of or slot in held:
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    if ink[y:y + 16, x:x + 16].any():
        continue
    if any_rect[y:y + 16, x:x + 16].any():
        n_blank_ft += 1
print('     (全盘) 空白但被记录压的格 = %d 个' % n_blank_ft)

print()
print('=' * 78)
print('⑥ 目标矩形清单 (搬运源): code / face 矩形 / 尺寸 / 格内墨')
print('=' * 78)
moves = []
for c in sorted(per_code):
    r = face_rect['large'][c]
    u0, v0, u1, v1 = r
    npx = int(ink[v0:v1, u0:u1].sum())
    moves.append(dict(code=c, char=nm_of(c), rect=list(r), w=u1 - u0, h=v1 - v0, ink=npx,
                      cells=len(per_code[c])))
    print('    0x%02X %-3s (%4d,%3d,%4d,%4d) %2dx%-2d 墨 %3d 格 %d'
          % (c, nm_of(c), u0, v0, u1, v1, u1 - u0, v1 - v0, npx, len(per_code[c])))
print('  合计 %d 条' % len(moves))

out = dict(iso=os.path.relpath(ISO, REPO).replace('\\', '/'),
           faces=[dict(name=nm, fld=fld, nrec=len(rs), nrect=len(face_rect[nm]))
                  for nm, fld, rs in faces],
           held_cells=len(held), moves=moves,
           per_face_mismatch=[[c, {k: v for k, v in rs.items()}] for c, rs in mis],
           free_zone=dict(y0=FREE_Y0, y1=FREE_Y1, ink=int(blk.sum()),
                          clean16=clean, rect_hits=n_hit),
           after_clear_blocked=[[s, x, y, [[nm, c, list(r)] for nm, c, r in a]]
                                for s, x, y, a in bad],
           blank_ft_cells=n_blank_ft)
io.open(os.path.join(HERE, 'recon.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print()
print('[rep] → %s' % os.path.join(HERE, 'recon.json'))
