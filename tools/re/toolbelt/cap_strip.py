# -*- coding: utf-8 -*-
r"""cap_strip.py -- ★ 右边缘 ASCII 条带 (x 992..1023) 的取证图: 它是什么 / 64 列方案把它怎么了

    python tools/re/toolbelt/cap_strip.py

产出 (全在 work\builds\GR_CAP2400\temp\):
  strip_base.png        基底盘 GR_ZH124 的 x 992..1023, y 0..303 (4 倍放大)
  strip_h660.png        h=660/62 探针盘的**同一区域** (应当与基底逐 texel 相同)
  strip_h644.png        h=644/64 探针盘的同一区域 (64 列 ⇒ 被网格格位覆盖)
  strip_compare.txt     三个区域的 sha256 + 逐 texel 差异 + 63 个矩形/182 条记录/码位清单
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', 'temp')
X0, X1, Y1 = 992, 1024, 304
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def plane_of(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    eft = [x for x in ent if x['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e['iso_off'], e['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _cov = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(eft['iso_off'], eft['stored']))))
    iso.close()
    return img, zx_lib.ft_records(ft, 28)[0], rec


def crop_png(img, path, scale=4):
    from PIL import Image
    sub = img[0:Y1, X0:X1]
    g = np.where(sub, 0, 255).astype(np.uint8)
    im = Image.frombytes('L', (X1 - X0, Y1), g).resize(((X1 - X0) * scale, Y1 * scale),
                                                      Image.NEAREST)
    im.save(path, optimize=True)
    return hashlib.sha256(bytes(g)).hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
    h660 = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', 'GR_CAP2400_h660.iso')
    h644 = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', 'GR_CAP2400_h644_clean.iso')
    ib, faces, rec = plane_of(base)
    P('=' * 92)
    P('右边缘条带取证: x %d..%d, y 0..%d ; 基底盘 = GR_ZH124 (%dx%d)'
      % (X0, X1 - 1, Y1 - 1, rec[2], rec[3]))
    strip = {}
    for (fn, _fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
                strip.setdefault(r, []).append((fn, k))
    P('[rect] 落在 x>=992 的 FT 记录: 不同矩形 **%d** 个, 被 **%d** 条记录引用'
      % (len(strip), sum(len(v) for v in strip.values())))
    per_face = {}
    for r, refs in strip.items():
        for (fn, k) in refs:
            per_face.setdefault(fn, []).append((r, k))
    for fn in per_face:
        ks = sorted(k for (_r, k) in per_face[fn])
        P('       face %-8s %3d 条 ; idx %d..%d ⇒ 码位 0x%02X..0x%02X'
          % (fn, len(ks), ks[0], ks[-1], ks[0] + 0x20, ks[-1] + 0x20))
    ink = int(ib[0:Y1, X0:X1].sum())
    P('[ink ] 该区域 Ink texel = **%d** / %d' % (ink, (X1 - X0) * Y1))
    sizes = {}
    for r in strip:
        sizes[(r[4] - r[2], r[5] - r[3])] = sizes.get((r[4] - r[2], r[5] - r[3]), 0) + 1
    P('[rect] 尺寸分布: %s ; 总 texel %d (= %.1f 个 16x16 格)'
      % (sizes, sum((r[4] - r[2]) * (r[5] - r[3]) for r in strip),
         sum((r[4] - r[2]) * (r[5] - r[3]) for r in strip) / 256.0))
    hb = crop_png(ib, os.path.join(OUT, 'strip_base.png'))
    P('[png ] strip_base.png   sha256(区域灰度)=%s' % hb)
    for tag, p in (('h660_c62', h660), ('h644_c64', h644)):
        im2, _f2, rec2 = plane_of(p)
        assert (rec2[2], rec2[3]) == (1024, rec2[3])
        h2 = crop_png(im2, os.path.join(OUT, 'strip_%s.png' % tag.split('_')[0]))
        d = int((im2[0:Y1, X0:X1] != ib[0:Y1, X0:X1]).sum())
        P('[png ] strip_%s.png sha256(区域灰度)=%s ; 与基底逐 texel 差异 = **%d**'
          % (tag, h2, d))
        # 逐矩形统计
        kept = 0
        for r in strip:
            if (im2[r[3]:r[5], r[2]:r[4]] == ib[r[3]:r[5], r[2]:r[4]]).all():
                kept += 1
        P('       %s: %d 个矩形中 **%d 个逐 texel 不变**, %d 个被改'
          % (tag, len(strip), kept, len(strip) - kept))
    with io.open(os.path.join(OUT, 'strip_compare.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUT, 'strip_compare.txt'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
