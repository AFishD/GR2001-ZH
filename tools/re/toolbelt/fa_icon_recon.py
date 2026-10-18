# -*- coding: utf-8 -*-
r"""fa_icon_recon.py — ✕ 图标源取证（只读）

    python tools/re/toolbelt/fa_icon_recon.py --iso <iso> --tag merge

① 从 COMMON.PAK 抠出 `pda_counterparts` 记录（256x256 PSM8）
② 按 icon_table.py 的 ELF 硬编码 UV 取 △(25,198)-(45,218) / ✕(1,198)-(21,218) 两个 20x20 精灵
③ 把图集 (new_font_revised) 的记录带 y=190..245 渲染出来, 看字库里到底有没有图标
"""
import argparse
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
import zx_lib                                                          # noqa: E402
import fa_recon as R                                                   # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')


def png_idx(a, path, scale=4, pal=None):
    from PIL import Image
    if pal is None:
        im = Image.fromarray(a.astype(np.uint8), 'L').resize(
            (a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)
    else:
        rgb = np.zeros(a.shape + (3,), dtype=np.uint8)
        for k, c in pal.items():
            rgb[a == k] = c
        im = Image.fromarray(rgb, 'RGB').resize(
            (a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    iso = T.Iso(a.iso)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    R.P('=' * 92)
    R.P('fa_icon_recon.py  iso=%s  COMMON.PAK %d B ; %d 条记录' % (a.iso, len(pak), len(recs)))
    R.P('=' * 92)
    for i, r in enumerate(recs):
        R.P('  rec#%-2d %-24s psm=0x%02X %dx%d clut=%d px_size=0x%X off=0x%X'
          % (i, r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
    hit = [r for r in recs if 'counterpart' in r[0].lower()]
    if not hit:
        R.P('[!!] COMMON.PAK 里没有 pda_counterparts 记录 —— 停手回报')
        return 1
    nm, psm, w, h, clut, px_size, PX = hit[0]
    R.P('[icon] 记录 %s : psm=0x%02X %dx%d clut_idx=%d px_size=%d px@0x%X'
      % (nm, psm, w, h, clut, px_size, PX))
    assert psm == 0x13 or psm == 0x14, hex(psm)
    # PSM8 (0x13): 1 字节/texel ; PSM4 (0x14): 半字节/texel
    if psm == 0x13:
        img = np.frombuffer(pak[PX:PX + w * h], dtype=np.uint8).reshape(h, w)
    else:
        raw = np.frombuffer(pak[PX:PX + w * h // 2], dtype=np.uint8).reshape(h, w // 2)
        img = np.zeros((h, w), dtype=np.uint8)
        img[:, 0::2] = raw & 0x0F
        img[:, 1::2] = raw >> 4
    png_idx(img, os.path.join(OUT, 'icon_%s' % a.tag, '%s_full.png' % nm), scale=3,
            pal={0: (255, 255, 255)})
    R.P('[icon] 全图 → %s' % os.path.join(OUT, 'icon_%s' % a.tag, '%s_full.png' % nm))
    for (label, box) in (('tri', (25, 198, 45, 218)), ('cross', (1, 198, 21, 218)),
                         ('band_v168_226', (0, 168, 256, 226))):
        x0, y0, x1, y1 = box
        sub = img[y0:y1, x0:x1]
        R.P('[icon] %-14s box=(%d,%d)-(%d,%d) %dx%d 非零 texel=%d'
          % (label, x0, y0, x1, y1, x1 - x0, y1 - y0, int((sub != 0).sum())))
        png_idx(sub, os.path.join(OUT, 'icon_%s' % a.tag, '%s_%s.png' % (nm, label)), scale=10,
                pal={0: (255, 255, 255)})
    iso.close()

    # ③ 字集记录带渲染
    F = R.read_font(a.iso)
    plane = F['plane']
    G = np.zeros((F['h'], F['w']), dtype=np.uint8)
    a2 = np.frombuffer(plane, dtype=np.uint8).reshape(F['h'], F['w'] // 2)
    G[:, 0::2] = (a2 & 0x0F)
    G[:, 1::2] = (a2 >> 4)
    for (label, y0, y1) in (('band194_245', 190, 246), ('atlas_full', 0, F['h'])):
        sub = G[y0:y1]
        png_idx(255 - sub * 17, os.path.join(OUT, 'atlas_%s' % a.tag, '%s.png' % label),
                scale=(2 if label == 'atlas_full' else 3))
    R.P('[atlas] 记录带/全图 → %s' % os.path.join(OUT, 'atlas_%s' % a.tag))
    with io.open(os.path.join(OUT, 'icon_recon_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(iso=a.iso, records=[dict(name=r[0], psm='0x%02X' % r[1], w=r[2], h=r[3],
                                                px_size=r[5], off='0x%X' % r[6]) for r in recs],
                       log=R.LOG), f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
