# -*- coding: utf-8 -*-
r"""fix_and_add_glyphs.py — 修复 28 个缺失字形 + 新增 146 字 (会话工具)

## 两个任务
  A) **修复既有缺陷**: 28 个字 (挥备榴规息给总据少屏范菜户振健像球白群馆做听痪瘫瞬硬顽饿)
     在 charset 里有码位, 但纹理格**空的** ⇒ 文本里显示为空白 (共 800+ 次出现)
  B) **新增 146 字**: 理想译名需要的字

## 分配策略
  · 28 个缺字形字 → 写回**它们自己的纹理格** (码位不变!)
  · 146 个新字     → 占用**剩余真空格** (345 个)

## 用法
  python fix_and_add_glyphs.py <src_iso> <dst_iso>
"""
import io
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import x12_lib as L  # noqa: E402

FZ16 = os.path.join(REPO, 'third_party/fonts/方正像素16.ttf')
CS = os.path.join(REPO, 'tools/font_pipeline/data/charset_compiled_zh16.json')
MENU_LBA = 776286
OFF_PAK_REC = 0x58431
PIX_OFF = 0x44C
NCOL, CW, CH, Y0, SR, SRS = 62, 16, 16, 2, 12, 3


def yrow(r):
    return Y0 + CH * (r + SRS * (r >= SR))


def render(ch, font):
    im = Image.new('L', (32, 32), 0)
    ImageDraw.Draw(im).text((4, 0), ch, font=font, fill=255)
    return (np.asarray(im)[0:16, 4:20] > 127)


def main(src, dst):
    cs = json.load(io.open(CS, encoding='utf-8'))
    pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
    have = set(cs['codes']) | set(pair_of)
    slot2char = {(l - 0xA1) * 94 + (t - 0xA1): ch for ch, (l, t) in pair_of.items()}

    A, _ = L.read_atlas(src)
    ink = (A == 0)
    H, W = A.shape

    # ---- A. 找缺字形的字 (有码位, 格空) ----
    fix = []          # (ch, slot, y0, x0)
    empty = []
    for r in range(50):
        y0 = yrow(r)
        if y0 + CH > H:
            break
        for c in range(NCOL):
            x0 = c * CW
            if x0 + CW > W:
                break
            if ink[y0:y0 + CH, x0:x0 + CW].sum() == 0:
                slot = r * NCOL + c
                if slot in slot2char:
                    fix.append((slot2char[slot], slot, y0, x0))
                else:
                    empty.append((slot, y0, x0))
    print('[A] 有码位无字形: %d 个 → 写回它们自己的格子' % len(fix))
    print('     %s' % ''.join(x[0] for x in fix))
    print('[B] 真空码位:     %d 个' % len(empty))

    # ---- 新字 ----
    MISSING = ('丁丹丽乔亨伟伯佐俊傅兰冈凡刘勃卜历史叶吕吴哥哲唐圣坤培夏奈奋姚娜孙宁宇宋宗'
               '富岩峰廉延弗彭彼徐志怀思恩戈戴扬斌斐昂晓普曹朱李杜杨杰柯柴桑楠欣欧歇殷毅毕汀'
               '汤沈泰洛津洪浩滕潘熊玉王玲珀珊珍琳琼瑞瑟略皮福穆米缪罕翁翔翰耶肖舒艾芬茨荣莉'
               '莱菲葆蒂蒙蓓蔡蕾袁詹费贾赖辉辛迈逊邹郑闫阮阳陈隆雅韦魏鲍鹏麦黛齐')
    new = [c for c in MISSING if c not in have]
    print('[B] 新字: %d 个, 需 %d 格 ⇒ %s'
          % (len(new), len(new), '✓ 够' if len(new) <= len(empty) else '✗ 不够'))

    font = ImageFont.truetype(FZ16, 16)
    A2 = A.copy()
    # A: 修复
    for ch, slot, y0, x0 in fix:
        A2[y0:y0 + CH, x0:x0 + CW] = np.where(render(ch, font), 0, 1).astype(np.uint8)
    # B: 新增
    assign = {}
    for i, ch in enumerate(new):
        slot, y0, x0 = empty[i]
        A2[y0:y0 + CH, x0:x0 + CW] = np.where(render(ch, font), 0, 1).astype(np.uint8)
        assign[ch] = dict(lead=0xA1 + slot // 94, trail=0xA1 + slot % 94,
                          slot=slot, x=x0, y=y0)
    print('[atlas] 修复 %d + 新增 %d = %d 格' % (len(fix), len(assign), len(fix) + len(assign)))

    # ---- 写盘 ----
    d = bytearray(open(src, 'rb').read())
    px = L.pack_atlas(A2)
    MENU = MENU_LBA * 2048
    assert bytes(d[MENU + OFF_PAK_REC + PIX_OFF:
                   MENU + OFF_PAK_REC + PIX_OFF + len(px)]) == L.pack_atlas(A), \
        '原像素平面不匹配'
    d[MENU + OFF_PAK_REC + PIX_OFF: MENU + OFF_PAK_REC + PIX_OFF + len(px)] = px
    open(dst, 'wb').write(bytes(d))

    # ---- 分配表 ----
    json.dump({'fix': [c for c, _, _, _ in fix],
               'assign': assign},
              io.open(os.path.join(HERE, 'glyph_full_assignment.json'), 'w',
                      encoding='utf-8'), ensure_ascii=False, indent=1)

    mx = max(v['lead'] for v in assign.values()) if assign else 0xA1
    print()
    print('  ⇒ 修复 %d 字 (码位不变, 文本立刻正常)' % len(fix))
    print('  ⇒ 新增 %d 字 (码位 lead 0xA1..0x%02X, 需 ≤ 0xB3: %s)'
          % (len(assign), mx, '✓' if mx <= 0xB3 else '✗'))
    print('  ⇒ 剩余真空码位 %d 个' % (len(empty) - len(assign)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
