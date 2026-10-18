# -*- coding: utf-8 -*-
r"""patch_zh100_single28_glyphs.py — 修 28 个单字节汉字"字形放错记录格"(round51/Lead)

现象(Lead 定性): 码位 0x80..0x9B 这 28 个单字节汉字的 FT 记录格里装的是别的字的字形
  (0x80..0x8F 装 +12/+13 码位的字; 0x90..0x9B 装 -16 码位的字), IoU 0.94~1.00 => 同字体、放错格。
  游戏里这 28 个字会显示成别的字; 它们在译文里各出现 1 次(共 28 处)。自 GR_ZH93 起就错。

修法: 用 方正像素16 重渲染这 28 个字, 写进各自的 FT 记录矩形(封包感知写入, 不碰 48B 包头)。
  幂等: 已修好的盘再跑 = 0 改动。自检: 写回后逐个与模板比 IoU, 要求 28/28 = 1.000。

用法:
  python tools/iso_build/patch_zh100_single28_glyphs.py --src <in.iso> --dst <out.iso> [--dry-run|--check-only]
"""
import argparse
import io
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                  # noqa: E402
from patch_zh94_glyph_align import Atlas               # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
CODES = list(range(0x80, 0x9C))                        # 28 个码位
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH100', 'temp', 'single28_report.json')


def render16(ch, fnt):
    from PIL import Image, ImageDraw
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dst')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()

    from PIL import ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    w = D.load_font(a.src)
    ad, pak_e, faces = w['atlas'], w['pak_e'], w['faces']
    PX, PSZ = ad['px_off'], ad['px_size']
    pak = ad['pak']
    iso_off = pak_e['iso_off']

    cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                        'charset_compiled_zh16.json'), encoding='utf-8'))
    code2ch = {v: k for k, v in cs['codes'].items()}

    rect_of = {}
    for fname, _fld, rs in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            code = idx + 0x20
            if code in CODES:
                rect_of.setdefault(code, (u0, v0, u1, v1))

    A = Atlas(bytearray(pak), PX, PSZ)
    En, _cov0 = A.decode_engine()
    empty_val = 1     # 空白 nibble = 1 (容器填充 0x11; 0 = 墨)

    plan, missing = [], []
    for code in CODES:
        ch = code2ch.get(code)
        if ch is None or code not in rect_of:
            missing.append(code)
            continue
        u0, v0, u1, v1 = rect_of[code]
        if (u1 - u0, v1 - v0) != (16, 16):
            missing.append(code)
            continue
        tgt = render16(ch, fnt)
        cur = En[v0:v1, u0:u1].astype(bool)
        diff = int(np.logical_xor(cur, tgt).sum())
        iou = float(np.logical_and(cur, tgt).sum()) / max(1, int(np.logical_or(cur, tgt).sum()))
        plan.append(dict(code=code, char=ch, rect=[u0, v0, u1, v1],
                         diff=diff, iou_before=round(iou, 4), tgt=tgt))

    print('[plan ] 待检 %d 个码位; 需要改像素 %d 个; 记录缺失/非16x16 %d 个'
          % (len(plan), sum(1 for p in plan if p['diff']), len(missing)))
    for p in plan[:6]:
        print('        %02X %s rect=%s diff=%d iou_before=%.3f'
              % (p['code'], p['char'], p['rect'], p['diff'], p['iou_before']))
    npx = sum(p['diff'] for p in plan)
    print('[plan ] 合计需要改 %d 像素' % npx)

    if a.check_only:
        print('[check] 只预检, 未写盘')
        return 0
    if a.dry_run:
        print('[dry  ] 未写盘')
        return 0
    if npx == 0:
        print('[done ] 无需改动 (幂等)')
        return 0
    if not a.dst:
        print('!! 需要 --dst')
        return 2

    for p in plan:
        u0, v0, u1, v1 = p['rect']
        En[v0:v1, u0:u1] = p['tgt']
    changed = np.where(En != A.eng)
    print('[pack ] 回写 %d 像素 (逐像素 set_px)' % len(changed[0]))
    for y, x in zip(changed[0].tolist(), changed[1].tolist()):
        A.set_px(int(x), int(y), bool(En[y, x]), empty_val)
    back, _c = A.decode_engine()
    assert (back == En).all(), '回写后引擎图与目标图不一致'

    shutil.copyfile(a.src, a.dst)
    with open(a.dst, 'r+b') as f:
        f.seek(iso_off + PX)
        f.write(bytes(A.nib))
    assert os.path.getsize(a.src) == os.path.getsize(a.dst)
    print('[iso  ] -> %s (尺寸不变)' % a.dst)

    w2 = D.load_font(a.dst)
    A2 = Atlas(bytearray(w2['atlas']['pak']), PX, PSZ)
    En2, _c2 = A2.decode_engine()
    ok = 0
    for p in plan:
        u0, v0, u1, v1 = p['rect']
        cur = En2[v0:v1, u0:u1].astype(bool)
        iou = float(np.logical_and(cur, p['tgt']).sum()) / max(1, int(np.logical_or(cur, p['tgt']).sum()))
        if iou >= 0.9999:
            ok += 1
        else:
            print('        !! %02X %s 修后 IoU=%.4f' % (p['code'], p['char'], iou))
    print('[ver  ] 修后与模板 IoU=1.000 的: %d / %d' % (ok, len(plan)))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
        tool='patch_zh100_single28_glyphs.py', src=a.src, dst=a.dst,
        codes=CODES, n_plan=len(plan), n_changed=sum(1 for p in plan if p['diff']),
        px=npx, verified_ok=ok,
        items=[{k: v for k, v in p.items() if k != 'tgt'} for p in plan]),
        ensure_ascii=False, indent=1))
    print('[report] %s' % os.path.relpath(REPORT, REPO))
    return 0 if ok == len(plan) else 3


if __name__ == '__main__':
    sys.exit(main())
