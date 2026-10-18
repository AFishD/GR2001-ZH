# -*- coding: utf-8 -*-
r"""fa_restore_check.py — 恢复源 (GR_F364/F365) 的独立校验（只读）

    python tools/re/toolbelt/fa_restore_check.py

① GR_F364 的槽 0..1735 是否与 GR_ZH124 (r84 成品) 逐 texel 相同 ⇒ 同一字形家族
② GR_F364 的槽 1736..1871 是否与 GR_F365 逐 texel 相同        ⇒ 两个独立盘互证
③ 把 1736..1871 的字形拼成对照图 (每格标 slot) 供人眼确认
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import tcslib as T                                                     # noqa: E402
import fa_recon as R                                                   # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')
B = lambda *a: os.path.join(REPO, 'work', 'builds', *a)


def main():
    os.makedirs(OUT, exist_ok=True)
    F364 = R.read_font(B('GR_F364', 'GR_F364.iso'))
    F365 = R.read_font(B('GR_F365', 'GR_F365.iso'))
    Z124 = R.read_font(B('GR_ZH124', 'GR_ZH124.iso'))
    cs = T.Charset()
    slot_char = {}
    for ch, pr in cs.enc_pair.items():
        slot_char[(pr[0] - 0xA1) * 94 + (pr[1] - 0xA1)] = ch
    R.P('=' * 92)
    R.P('fa_restore_check.py  ① F364(%.0fx%d) vs ZH124(%.0fx%d) 槽 0..1735  ② F364 vs F365 槽 1736..1871'
      % (F364['w'], F364['h'], Z124['w'], Z124['h']))
    R.P('=' * 92)
    res = {}

    def cells(F, ncol, slots):
        out = {}
        for s in slots:
            cx, cy = R.cell(s, ncol)
            out[s] = R.window(F['plane'], F['w'], cx, cy, 16, 16)
        return out

    for tag, (fa, na), (fb, nb), lo, hi in (('A_0_1735', (F364, 62), (Z124, 62), 0, 1735),
                                            ('B_1736_1871', (F364, 62), (F365, 62), 1736, 1871)):
        ca = cells(fa, na, range(lo, hi + 1))
        cb = cells(fb, nb, range(lo, hi + 1))
        bad = [s for s in ca if not (ca[s] == cb[s]).all()]
        ink_a = {s: int(ca[s].sum()) for s in ca}
        R.P('[%s] 槽 %d..%d (%d 格): 逐 texel 不同 %d 个 %s ; 墨 min/max = %d/%d ; 空格 %d'
          % (tag, lo, hi, hi - lo + 1, len(bad), '✓' if not bad else '✗ %s' % bad[:10],
             min(ink_a.values()), max(ink_a.values()),
             sum(1 for v in ink_a.values() if v == 0)))
        res[tag] = dict(lo=lo, hi=hi, n=hi - lo + 1, diff=len(bad), bad=bad[:20],
                        ink_min=min(ink_a.values()), ink_max=max(ink_a.values()),
                        empty=sum(1 for v in ink_a.values() if v == 0))

    # ③ 对照图: 1736..1871 每格 + 字符标注
    from PIL import Image, ImageDraw
    slots = list(range(1736, 1872))
    S, pad, cols = 5, 3, 16
    rows = (len(slots) + cols - 1) // cols
    tile = 16 * S
    sheet = Image.new('RGB', (cols * (tile + pad) + pad, rows * (tile + pad + 10) + pad),
                      (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    ca = cells(F364, 62, slots)
    for i, s in enumerate(slots):
        g = ca[s]
        im = Image.fromarray(np.where(g, 0, 255).astype(np.uint8), 'L').resize(
            (tile, tile), Image.NEAREST).convert('RGB')
        x = pad + (i % cols) * (tile + pad)
        y = pad + (i // cols) * (tile + pad + 10)
        sheet.paste(im, (x, y))
        dr.text((x, y + tile + 1), '%d %s' % (s, slot_char.get(s, '?')), fill=(0, 0, 0))
    p = os.path.join(OUT, 'restore_slots_1736_1871_F364.png')
    sheet.save(p)
    R.P('[sheet] %s' % p)

    with io.open(os.path.join(OUT, 'restore_check.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
