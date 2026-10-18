# -*- coding: utf-8 -*-
r"""verify_record_band.py — 独立复核最终盘 GR_ZH97 的"记录带 y=353 已恢复字体模板"。

不信任补丁自己的自检输出, 直接**从两张 ISO 现读**:
  · COMMON.PAK → new_font_revised 像素容器 (引擎口径解码, 复用 patch_zh94_glyph_align.Atlas);
  · FONT.RES → 3 个 face 的 FT 记录矩形;
  · charset 单字节表 + 方正像素16.ttf 模板。

产出:
  · 溢出带行 {353,369,385,401,417,433} 上, 每格 (矩形) 修前/修后 的差异 texel 数;
  · 20 个"行 18 单字节记录格" 的 y=353 行 ASCII 对照 (修前 / 修后 / 模板);
  · 全图集差异 texel 总数 + 行分布 (应当只有 y=353, 76 个);
  · JSON 落盘。

用法: python verify_record_band.py <A.iso(修前)> <B.iso(修后)> [--json out.json]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                  # noqa: E402
import tcslib                                                       # noqa: E402
from patch_zh94_glyph_align import Atlas                            # noqa: E402

W, H = 1024, 512
ROWS = list(range(19, 25))
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


SPILL = sorted(yrow(r) - 1 for r in ROWS)


def load(iso_path):
    iso = tcslib.Iso(iso_path)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
        elif e['name'] == 'FONT.RES':
            ft_e = e
        if pak_e and ft_e:
            break
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised'][0]
    A = Atlas(pak, rec[6], rec[5])
    _he, faces = tcslib.parse_ft_faces(ft_blob)
    return A, faces, pak, rec


def render16(ch, fnt):
    from PIL import Image, ImageDraw
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    A_iso, B_iso = a[0], a[1]
    outp = a[a.index('--json') + 1] if '--json' in a else os.path.join(HERE, 'record_band_verify.json')
    from PIL import ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    cs = tcslib.Charset()
    rev = dict((b, c) for c, b in cs.enc_single.items())

    Aa, faces, _pakA, _recA = load(A_iso)
    Ab, _facesB, _pakB, _recB = load(B_iso)
    print('修前 %s : 引擎图墨 %d' % (A_iso, int(Aa.eng.sum())))
    print('修后 %s : 引擎图墨 %d' % (B_iso, int(Ab.eng.sum())))

    d = (Aa.eng != Ab.eng)
    ys = sorted(set(int(y) for y in np.where(d.any(axis=1))[0]))
    print('')
    print('全图集差异 texel = %d; 落在行 %s (溢出带 %s)'
          % (int(d.sum()), ys, SPILL))

    # 记录矩形 (3 face 去重)
    rects = {}
    for fname, _fld, rs in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            rects.setdefault((u0, v0, u1, v1), dict(faces=set(), codes=set()))
            rects[(u0, v0, u1, v1)]['faces'].add(fname)
            rects[(u0, v0, u1, v1)]['codes'].add(idx + 0x20)

    recs = []
    for (u0, v0, u1, v1) in sorted(rects):
        if not [s for s in SPILL if v0 <= s < v1]:
            continue
        if (u1 - u0, v1 - v0) != (16, 16):
            recs.append(dict(rect=[u0, v0, u1, v1], kind='icon', chars=[], codes=[],
                             faces=sorted(rects[(u0, v0, u1, v1)]['faces']),
                             diff_texels=int(d[v0:v1, u0:u1].sum()),
                             diff_rows=[], template_ok=None))
            continue
        chars = sorted(set(rev[c] for c in rects[(u0, v0, u1, v1)]['codes'] if c in rev))
        nd = int(d[v0:v1, u0:u1].sum())
        rows = sorted(set(int(v0 + y) for y in np.where(d[v0:v1, u0:u1].any(axis=1))[0]))
        ent = dict(rect=[u0, v0, u1, v1], chars=chars,
                   codes=sorted('0x%02X' % c for c in rects[(u0, v0, u1, v1)]['codes']),
                   faces=sorted(rects[(u0, v0, u1, v1)]['faces']),
                   diff_texels=nd, diff_rows=rows, template_ok=None)
        if chars:
            tpl = render16(chars[0], fnt)
            ent['template_ok'] = bool((Ab.eng[v0:v1, u0:u1] == tpl).all())
            ent['template_ok_before'] = bool((Aa.eng[v0:v1, u0:u1] == tpl).all())
        recs.append(ent)

    fixed = [r for r in recs if r['diff_texels'] > 0]
    print('')
    print('压在溢出带行上的记录矩形 %d 个; 其中修前/修后有差异的 **%d 个**, '
          '差异合计 %d texel' % (len(recs), len(fixed), sum(r['diff_texels'] for r in fixed)))
    print('这些格的差异行 (应当只有 353): %s'
          % sorted(set(rr for r in fixed for rr in r['diff_rows'])))
    print('修后与 方正像素16 模板逐像素相同的格: %d / %d'
          % (sum(1 for r in fixed if r['template_ok']), len(fixed)))
    print('修前就与模板相同的格 (应当 0): %d'
          % sum(1 for r in fixed if r['template_ok_before']))
    print('')
    print('逐格:')
    for r in fixed:
        print('  %-4s rect(u=%4d..%4d, v=%3d..%3d) 差异 %2d texel 行 %s 码 %s 模板= %s'
              % (''.join(r['chars']), r['rect'][0], r['rect'][2], r['rect'][1], r['rect'][3],
                 r['diff_texels'], r['diff_rows'], ','.join(r['codes']),
                 'OK' if r['template_ok'] else 'NO'))


    def ascii_row(img, u0, v, n=16):
        return ''.join('#' if img[v, u0 + i] else '.' for i in range(n))

    print('')
    print('=== y=353 那一行的 ASCII 对照 (# = 墨) ===')
    print('%-4s %-8s %-20s %-20s %-20s' % ('字', '码', '修前', '修后', '方正像素16 模板'))
    for r in fixed:
        u0, v0 = r['rect'][0], r['rect'][1]
        v = 353 if v0 <= 353 < r['rect'][3] else r['diff_rows'][0]
        tpl = render16(r['chars'][0], fnt)
        print('%-4s %-8s %-20s %-20s %-20s  模板行=%s'
              % (''.join(r['chars']), ','.join(r['codes']),
                 '|%s|' % ascii_row(Aa.eng, u0, v), '|%s|' % ascii_row(Ab.eng, u0, v),
                 '|%s|' % ascii_row(tpl, 0, v - v0), 'OK' if r['template_ok'] else 'NO'))

    doc = dict(A=os.path.abspath(A_iso), B=os.path.abspath(B_iso),
               spill_rows=SPILL, atlas_diff_texels=int(d.sum()), atlas_diff_rows=ys,
               ink_before=int(Aa.eng.sum()), ink_after=int(Ab.eng.sum()),
               rects=recs, fixed_rects=len(fixed),
               fixed_texels=sum(r['diff_texels'] for r in fixed),
               all_template_ok=all(r['template_ok'] for r in fixed))
    io.open(outp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('')
    print('→ %s' % outp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
