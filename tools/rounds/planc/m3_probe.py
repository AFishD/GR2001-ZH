# -*- coding: utf-8 -*-
r"""m3_probe.py — 追查"每行尾部几列对不上"的真相 + 全图集格占用图。

1) 对指定的"尾部列"字, 在整张图集里穷举搜索它的真位置 (16 对齐 x, 全部 y);
2) 打印 b20_map.json 对同一批字的匹配结果;
3) 打印 16x16 (x=16k) 网格的占用矩阵 (每行有多少格有墨), 以及 y>=354 下半区的空格清单。
只读。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))

import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import tcslib                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
B20 = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'b20_map.json')
W, H, CW, CH = 1024, 512, 16, 16


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


iso = tcslib.Iso(ISO)
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)

js = json.load(open(CS, encoding='utf-8'))
pair_of = js['pair_of']
fnt = ImageFont.truetype(FZ, 16)


def render(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def best_pos(ch, ymin=0, ymax=H):
    t = render(ch)
    if not t.any():
        return None
    best = (10 ** 9, None, None)
    for y in range(ymin, ymax - CH + 1):
        win_all = INK[y:y + CH]
        for k in range(0, W - CW + 1, 16):
            m = int((win_all[:, k:k + CW] != t).sum())
            if m < best[0]:
                best = (m, k, y)
                if m == 0:
                    return best
    return best


print('== 尾部列字的真实位置 (全图集穷举, 16 对齐) ==')
targets = []
for ch, C in (('服', 58), ('杆', 59), ('点', 60), ('住', 61), ('止', 52), ('辑', 57),
              ('南', 0), ('国', 4), ('容', 5), ('试', 1), ('达', 3), ('之', 58), ('加', 61)):
    b = pair_of.get(ch)
    if not b:
        continue
    s = (b[0] - 0xA1) * 94 + (b[1] - 0xA1)
    R, C2 = s // 62, s % 62
    m, x, y = best_pos(ch)
    print('  %s pair=%02X%02X slot=%4d R=%2d C=%2d  期望格=(%4d,%3d)  实测最佳=(%4d,%3d) mismatch=%d'
          % (ch, b[0], b[1], s, R, C2, 16 * ((C2 + 6) % 64), yrow(R), x if x is not None else -1,
             y if y is not None else -1, m))

M = json.load(open(B20, encoding='utf-8'))['map']
print()
print('== b20_map.json 对同一批字的匹配 ==')
for ch in ('服', '杆', '点', '住', '止', '辑', '南', '国', '容', '试', '达', '之', '加', '的', '你'):
    v = M.get(ch)
    if v is None:
        print('  %s : 未匹配' % ch)
    else:
        b = pair_of.get(ch)
        s = (b[0] - 0xA1) * 94 + (b[1] - 0xA1) if b else -1
        print('  %s : (x=%4d, y=%3d, score=%3d)  slot=%4d row=%2d' % (ch, v[0], v[1], v[2], s,
                                                                     s // 62 if s >= 0 else -1))

print()
print('== 16x16 网格占用 (x=16k) 每行有墨格数 / 全空格数 ==')
print('   y    有墨格数  全空(x=16k)格数   空格 x 列表(前 20)')
for r in range(0, 32):
    y = yrow(r)
    if y + CH > H:
        print('  %3d   (越界 y+16=%d > %d)' % (y, y + CH, H))
        continue
    inked, free = [], []
    for k in range(64):
        n = int(INK[y:y + CH, 16 * k:16 * k + CW].sum())
        (inked if n else free).append(k)
    print('  %3d(r%2d)   %3d        %3d          %s' % (y, r, len(inked), len(free), free[:20]))
