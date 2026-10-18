# -*- coding: utf-8 -*-
r"""font_cell_map.py — 画一张"**所有格 + 可用格 + 可回收格**"的字库格位图（人眼一眼看懂）

## 图集上叠着两套布局

  ① **对偶槽位 1504 个**（引擎按 `col = slot % 62` 寻址的 62x25 网格）—— 汉字字形放这里；
  ② **FT 记录矩形**（3 个 face 共 544 条非空）—— 单字节汉字 / ASCII / 拉丁字母 / 引擎滚动箭头 /
     空格放这里；它们**不对齐 16x16**，而且和 ① 在同一片纹理上**部分重叠**。

## 槽位分类（round52 订正）

★ 关键订正：**空格里有墨 ≠ 可以清**。要看那块墨**归谁**：

  某槽位的墨 ⊂ 某条【活 FT 记录】的矩形  ⇒ 那是**活字形**（单字节字/ASCII/箭头/çñ），**不可回收**
  否则                                  ⇒ **可回收的旧墨**（没人要）

| 颜色 | 状态 | 含义 |
|---|---|---|
| 深绿框 + 浅绿底 | `used` | **在用格**：charset 里的汉字占着 |
| 亮绿框 + 白底 | `free_blank` | ★ **可用格**：空白 ⇒ 可直接写新字 |
| 紫框 + 淡紫底 | `held_ft` | **被活字形占着**（其上有 FT 记录的单字节字/箭头/çñ）⇒ 要用得先搬走那个字形 |
| 橙框 + 橙底 | `recyclable` | **可回收**：墨没人要 ⇒ 清掉即变可用格 |
| 灰框 | `dead_pair` | 死 pair（lead 越界） |
| **蓝框** | `ft_record` | FT 记录矩形（引擎真正采样的字形窗；含 16 条记录共用的"空格/未用码"空矩形） |

## 输出
  <out>/<prefix>_font_cell_map.png    格位图（标题/统计/图例/公式 + FT 矩形上标码位）
  <out>/<prefix>_font_cell_map.csv    逐槽位数据（含 owner 列：这块墨归哪条记录）

用法:
  python tools/iso_build/font_cell_map.py --iso <iso> --out <dir> [--prefix GR_ZH102] [--scale 2]
"""
import argparse
import csv
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}      # 引擎硬编码滚动箭头 / 图标码记录槽

COL = {
    'used':       ((120, 220, 130), (20, 130, 40)),
    'free_blank': ((255, 255, 255), (0, 190, 90)),
    'free_ft':    ((255, 245, 170), (200, 170, 0)),      # ★ 空白但被 FT 记录压着 ⇒ 不是安全可用格
    'held_ft':    ((215, 195, 245), (140, 60, 200)),
    'recyclable': ((255, 200, 120), (235, 110, 0)),
    'dead_pair':  ((205, 205, 205), (110, 110, 110)),
    'ft_record':  ((120, 170, 255), (0, 60, 220)),
}
LEGEND = [
    ('used', '在用格 (charset 汉字)'),
    ('free_blank', '★ 可用格 (空白且不被记录压)'),
    ('free_ft', '空白但被 FT 记录压着 ⇒ 写进去会污染那条记录'),
    ('held_ft', '被活字形占着 (FT 记录的单字节字/箭头/çñ)'),
    ('recyclable', '可回收 (墨没人要 ⇒ 清掉即可用)'),
    ('ft_record', 'FT 记录矩形 (含空格/未用码共用的空框)'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--prefix', default=None)
    ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args()
    prefix = a.prefix or os.path.splitext(os.path.basename(a.iso))[0]
    os.makedirs(a.out, exist_ok=True)

    w = D.load_font(a.iso)
    ad, faces = w['atlas'], w['faces']
    W, H = ad['w'], ad['h']
    g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
    ink = g < 128
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}

    # 正文里出现过的字符（决定"活"）
    occ = {}
    tdir = os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'text')
    if os.path.isdir(tdir):
        for fn in os.listdir(tdir):
            if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
                with io.open(os.path.join(tdir, fn), encoding='utf-8-sig', newline='') as f:
                    for row in csv.DictReader(f):
                        for ch in (row.get('text_edited') or ''):
                            occ[ch] = occ.get(ch, 0) + 1
    if not occ:
        print('!! 警告: 没读到文本表 (%s) ⇒ 所有单字节字都会被当成"非活", 分类不可信' % tdir)

    def is_live(code):
        if code in KEEP_HARD or 0x20 <= code <= 0x7E:
            return True
        if code in code2ch:
            return occ.get(code2ch[code], 0) > 0
        return False

    # ── FT 记录矩形 ──────────────────────────────────────────────────
    rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
    rect_of = {}
    for idx, r in enumerate(rec):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            rect_of[idx + 0x20] = (u0, v0, u1, v1)
    live_mask = np.zeros((H, W), dtype=bool)
    for c, (u0, v0, u1, v1) in rect_of.items():
        if is_live(c):
            live_mask[v0:v1, u0:u1] = True

    # ── 槽位 ─────────────────────────────────────────────────────────
    slot_of, dead = {}, {}
    for ch, (b1, b2) in cs['pair_of'].items():
        s = tcslib.pair_slot(b1, b2)
        (slot_of if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI else dead)[s] = ch

    rows = []
    cnt = dict(used=0, free_blank=0, free_ft=0, held_ft=0, recyclable=0, dead_pair=0, unaddressable=0)
    # 所有 FT 记录矩形 (含非活) —— 用来判"空白格会不会被记录压到"
    any_ft = np.zeros((H, W), dtype=bool)
    for _c, (u0, v0, u1, v1) in rect_of.items():
        any_ft[v0:v1, u0:u1] = True
    for slot in range(1504):
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        ok = (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H)
        cell = ink[y:y + 16, x:x + 16] if ok else np.zeros((16, 16), bool)
        n = int(cell.sum())
        owner = ''
        if not ok:
            st = 'unaddressable'
        elif slot in dead:
            st = 'dead_pair'
        elif slot in slot_of:
            st = 'used'
        elif n == 0:
            # ★ 空白也要看有没有 FT 记录压着: 压着 ⇒ 写进去会污染那条记录的字形
            if ok and any_ft[y:y + 16, x:x + 16].any():
                st = 'free_ft'
                own = [('0x%02X' % c) for c, (u0, v0, u1, v1) in rect_of.items()
                       if x < u1 and x + 16 > u0 and y < v1 and y + 16 > v0]
                owner = ' '.join(own[:4]) + (' …共%d条' % len(own) if len(own) > 4 else '')
            else:
                st = 'free_blank'
        else:
            held = int((cell & live_mask[y:y + 16, x:x + 16]).sum())
            if held == n:
                st = 'held_ft'
                own = [('0x%02X' % c) for c, (u0, v0, u1, v1) in rect_of.items()
                       if is_live(c) and x < u1 and x + 16 > u0 and y < v1 and y + 16 > v0]
                owner = ' '.join(own[:3])
            else:
                st = 'recyclable'
        cnt[st] += 1
        rows.append(dict(slot=slot, row=slot // 62, col=slot % 62, x=x, y=y, status=st,
                         char=slot_of.get(slot, dead.get(slot, '')), owner=owner, ink_px=n,
                         code=('%02X%02X' % tuple(cs['pair_of'][slot_of[slot]])) if slot in slot_of else ''))

    used_mask = np.zeros((H, W), dtype=bool)
    for slot in slot_of:
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        used_mask[y:y + 16, x:x + 16] = True
    n_recyclable = int((ink & ~used_mask & ~live_mask).sum())

    # ── 画 ───────────────────────────────────────────────────────────
    S = a.scale
    PAD, HDR = 14, 150
    base = Image.fromarray(g).convert('RGB').resize((W * S, H * S), Image.NEAREST)
    arr = np.asarray(base).astype(np.float32)

    def tint(x0, y0, x1, y1, color, alpha):
        X0, Y0 = max(0, x0 * S), max(0, y0 * S)
        X1, Y1 = min(W * S, x1 * S), min(H * S, y1 * S)
        if X1 > X0 and Y1 > Y0:
            arr[Y0:Y1, X0:X1] = arr[Y0:Y1, X0:X1] * (1 - alpha) + np.array(color, np.float32) * alpha

    for r in rows:
        if r['status'] in ('unaddressable', 'used'):
            continue
        tint(r['x'], r['y'], r['x'] + 16, r['y'] + 16, COL[r['status']][0],
             0.55 if r['status'] == 'free_blank' else 0.42)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for r in rows:
        if r['status'] == 'unaddressable':
            continue
        d.rectangle([r['x'] * S, r['y'] * S, r['x'] * S + 16 * S - 1, r['y'] * S + 16 * S - 1],
                    outline=COL[r['status']][1], width=1)
    # FT 矩形 + 码位标注（只标"压在槽位上"或宽>=8px 的，避免糊成一片）
    try:
        ft_txt = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', max(9, S * 5))
    except Exception:
        ft_txt = ImageFont.load_default()
    for c, (u0, v0, u1, v1) in sorted(rect_of.items()):
        d.rectangle([u0 * S, v0 * S, u1 * S - 1, v1 * S - 1], outline=COL['ft_record'][1], width=1)
        overlaps = any(not (x >= u1 or x + 16 <= u0 or y >= v1 or y + 16 <= v0)
                       for x, y in (tcslib.atlas_cell_xy_engine_view(s) for s in range(1504)))
        if overlaps and (u1 - u0) >= 7:
            lab = '0x%02X' % c
            if c in code2ch:
                lab += code2ch[c]
            elif c == 0x20:
                lab += '空格'
            d.text((u0 * S + 1, v0 * S + 1), lab, fill=(0, 40, 200), font=ft_txt)

    Wc = W * S
    canvas = Image.new('RGB', (Wc + PAD * 2, H * S + HDR + PAD * 2), (255, 255, 255))
    canvas.paste(img, (PAD, HDR))
    dc = ImageDraw.Draw(canvas)
    try:
        f1 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
        f2 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 15)
    except Exception:
        f1 = f2 = ImageFont.load_default()

    dc.text((PAD, 8), '%s 字库格位图 —— 所有格 %d 个对偶槽位 + %d 条 FT 记录窗'
            % (prefix, len(rows), len(rect_of)), fill=(0, 0, 0), font=f1)
    dc.text((PAD, 36), '在用 %d   ★可用(空白且不被记录压) %d   空白但被记录压 %d   被活字形占着 %d   '
                       '可回收 %d   死pair %d'
            % (cnt['used'], cnt['free_blank'], cnt['free_ft'], cnt['held_ft'],
               cnt['recyclable'], cnt['dead_pair']), fill=(60, 60, 60), font=f2)
    dc.text((PAD, 58), '图集墨 %d px = 在用格内 %d + 活字形(FT记录) %d + 可回收 %d'
            % (int(ink.sum()), int((ink & used_mask).sum()),
               int((ink & live_mask & ~used_mask).sum()), n_recyclable),
            fill=(60, 60, 60), font=f2)
    lx = PAD
    for key, label in LEGEND:
        fill, bd = COL[key]
        dc.rectangle([lx, 86, lx + 22, 106], fill=fill, outline=bd, width=2)
        dc.text((lx + 28, 88), label, fill=(30, 30, 30), font=f2)
        lx += 34 + int(dc.textlength(label, font=f2))
    dc.text((PAD, 118), '槽位: slot=(lead-0xA1)*94+(trail-0xA1); row=slot//62; col=slot%62; '
                        'cell=(16*col, 2+16*(row+3*(row>=12)))   |   FT 记录: idx=code-0x20, 引擎按矩形原样采样',
            fill=(110, 110, 110), font=f2)

    png = os.path.join(a.out, prefix + '_font_cell_map.png')
    canvas.save(png)
    csvp = os.path.join(a.out, prefix + '_font_cell_map.csv')
    with io.open(csvp, 'w', encoding='utf-8-sig', newline='') as f:
        wtr = csv.DictWriter(f, fieldnames=['slot', 'row', 'col', 'x', 'y', 'status',
                                            'char', 'code', 'owner', 'ink_px'], lineterminator='\r\n')
        wtr.writeheader()
        for r in rows:
            wtr.writerow(r)

    print('[格位图] %s  (%dx%d)' % (os.path.relpath(png, REPO), canvas.width, canvas.height))
    print('[数据]   %s' % os.path.relpath(csvp, REPO))
    print('[统计] 对偶槽位 %d = 在用 %d + **可用(空白且不被记录压) %d** + 空白但被记录压 %d '
          '+ 被活字形占着 %d + 可回收 %d + 死pair %d + 不可寻址 %d'
          % (len(rows), cnt['used'], cnt['free_blank'], cnt['free_ft'], cnt['held_ft'],
             cnt['recyclable'], cnt['dead_pair'], cnt['unaddressable']))
    print('       ★ 安全可用格 = 可用 %d (把"空白但被记录压"的 %d 个排除掉; 那些格写进去会污染对应记录)'
          % (cnt['free_blank'], cnt['free_ft']))
    print('[统计] FT 记录 %d 条 (活 %d / 非活 %d) ; 可回收墨 %d px'
          % (len(rect_of), sum(1 for c in rect_of if is_live(c)),
             sum(1 for c in rect_of if not is_live(c)), n_recyclable))
    return 0


if __name__ == '__main__':
    sys.exit(main())
