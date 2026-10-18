# -*- coding: utf-8 -*-
r"""patch_zh95_ft_single_glyphs.py — 把 6 个"点到了格子里、却画不出来"的单字节汉字补回图集。

## 症状 (round46 实测, 见 docs/REPORT_font_repack.md §6)

`FONT.RES` 的 FT 记录表里有 7 条记录被改到了**图集最底下一行** (网格行 24, y=434..450):

    0x92 若 / 0x9D 纤 / 0x9E 终 / 0x9F 脆 / 0xA0 膛 / 0xAE 荐 / 0xFF 著

它们的**字形位置只写对了一半**: 位图被写在 **flat 容器坐标** (u0, v0), 而引擎按
**引擎图坐标** (u0, v0) 采样 (round45 实机 A/B 已证: 记录矩形在哪, 字就在哪)。
行 24 属于第 6 段 (y 384..447) ⇒ flat 列比引擎列多 96×7=672 texel ⇒ 两者**不是同一个地方**:

    flat(u0, 434)  ↔  引擎((u0 − 672) mod 1024, 433)     ← 字形落到了行 23 的某个**对偶格**里

后果: 这 6 个字在游戏里**画出来是空白**(或别人的像素), 而它们所在的那几个对偶格
被别人的字形顶着。GR_ZH93 的旧口径 GlyphCache 读 flat 行 ⇒ 当年判"有字形"没发现;
round45 把 `_nibbles` 改成读引擎行以后, 这几条记录就**露馅**了 —— 但 round45 之后
行 23 的相邻字形有 1~2 行像素渗进 ±4/±2 容差窗, 于是预检又被"蒙"过去 (假通过)。
round46 的紧凑重排把行 23 的格全部重写 ⇒ 渗漏消失 ⇒ 整体重编码时预检如实报出缺字。

## 本补丁做什么

把 6 个字的位图**写到引擎真正采样的位置** = 记录矩形本身 (u0, v0, u0+16, v0+16)。
位图来源: `third_party/fonts/方正像素16.ttf` 按 `tools/font_pipeline/gen_font16.py`
的 `render16()` 同款配方渲染 (draw origin (8,8) → canvas[8:24, 8:24] → 阈值 <128)。
**并且与 GR_ZH93 的 flat 位图逐像素核对** (那份是当年写进去的原图):
实测 6 个字 **IoU = 1.000** ⇒ 补回去的**就是原来那张图**, 不是重新造的字。

· 只动这 6 条记录窗里的像素 (它们现在是**全空**的 ⇒ 不覆盖任何东西);
· 走 GIF 封包换算 (`repack_font.Atlas`), **不碰 48B 包头**;
· `0xAE 荐` 已在 round40 改成对偶码, 它的记录是**休眠**的 ⇒ 不动;
· 一次性补丁: 补完以后所有后续版本都继承 (重排的保护掩码把记录矩形当"别人的采样窗",
  一个像素都不会碰 ⇒ 修好的字形不会丢)。

用法:
  python tools/iso_build/patch_zh95_ft_single_glyphs.py <src.iso> <dst.iso> [--dry-run]
"""
import argparse
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:                                                    # noqa: BLE001
    pass

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
ZH93 = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                      'ft_single_glyph_fix.json')
GRID_ROW = 24                        # 出问题的那一行 (y = 434)


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS
                                              if r >= tcslib.GRID_SKIP_ROW else 0))


def render16(ch):
    """与 tools/font_pipeline/gen_font16.py::render16 同款: 方正像素16 → 16x16 布尔墨窗。"""
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    out = np.asarray(img)[8:24, 8:24] < 128
    if not out.any():
        raise SystemExit('!! 方正像素16 渲染不出 %r' % ch)
    return out


def flat_view(A):
    """「整个容器当裸图」视图 (旧口径) —— 只用来跟 GR_ZH93 的原始位图核对。"""
    stride = A.w // 2
    n = min(len(A.cont) // stride, A.h)
    a = np.frombuffer(bytes(A.cont[:n * stride]), dtype=np.uint8).reshape(n, stride)
    img = np.zeros((A.h, A.w), dtype=bool)
    img[:n, 0::2] = (a & 0x0F) == 0
    img[:n, 1::2] = (a >> 4) == 0
    return img


def iou(a, b):
    u = int((a | b).sum())
    return 1.0 if u == 0 else int((a & b).sum()) / u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    print('=' * 78)
    print('补 FONT.RES 单字节记录窗 (网格行 %d) 的缺失字形' % GRID_ROW)
    print('  src = %s' % rel(src))
    print('=' * 78)

    font = dump_font.load_font(src)
    am = font['atlas']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    cs = tcslib.Charset()
    recs = [x for x in font['faces'] if x[0] == 'default'][0][2]

    # ---- 目标清单: default face 里 v0 == yrow(24) 且确实是本盘在用的单字节汉字 ----
    targets, skipped = [], []
    for idx, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        if v0 != yrow(GRID_ROW) or u1 <= u0 or v1 <= v0:
            continue
        code = idx + 0x20
        ch = cs.codes.get(code)
        if ch is None:
            skipped.append(dict(code=code, rect=[u0, v0, u1, v1],
                                why='该字节现在没有映射 (改成对偶码了) ⇒ 记录是休眠的, 不动'))
            continue
        targets.append(dict(code=code, char=ch, rect=[u0, v0, u1, v1]))
    print('[找  ] 落在行 %d 的记录: %d 条 (要补 %d, 跳过 %d)'
          % (GRID_ROW, len(targets) + len(skipped), len(targets), len(skipped)))
    for x in skipped:
        print('       skip 0x%02X %s — %s' % (x['code'], x['rect'], x['why']))

    # ---- 位图: TTF 渲染 + 与 GR_ZH93 原始 flat 位图核对 ----
    F93 = None
    if os.path.isfile(ZH93):
        f93 = dump_font.load_font(ZH93)
        a93 = f93['atlas']
        A93 = repack_font.Atlas(a93['pak'], a93['px_off'], a93['px_size'],
                                a93['w'], a93['h'], a93['psm'])
        F93 = flat_view(A93)
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        assert (u1 - u0, v1 - v0) == (tcslib.CW, tcslib.CH), x
        g = render16(x['char'])
        x['ink_ttf'] = int(g.sum())
        x['engine_ink_before'] = int(A.eng[v0:v1, u0:u1].sum())
        if F93 is not None:
            old = F93[v0:v1, u0:u1]
            x['zh93_flat_ink'] = int(old.sum())
            x['zh93_iou'] = round(iou(g, old), 4)
            if x['zh93_iou'] < 0.98:
                raise SystemExit('!! %s: 补回去的位图与 GR_ZH93 里那张不一样 (IoU=%.3f) —— '
                                 '拒绝改写' % (x['char'], x['zh93_iou']))
        x['bitmap'] = g
    print('[图  ] 6 个位图与 GR_ZH93 原始位图 IoU = %s'
          % ' '.join('%s:%.3f' % (x['char'], x['zh93_iou']) for x in targets))

    # ---- 写入前的安全前提: 目标窗要么全空, 要么只剩"不是字形的残渣" ----
    bad, noise = [], []
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        cur = A.eng[v0:v1, u0:u1]
        x['engine_ink_before'] = int(cur.sum())
        if x['engine_ink_before'] == 0:
            continue
        i = iou(cur, x['bitmap'])
        frac = x['engine_ink_before'] / max(1, int(x['bitmap'].sum()))
        if i < 0.5 and frac < 0.4:
            x['noise_iou'] = round(i, 3)
            x['noise_frac'] = round(frac, 3)
            noise.append(x)
        else:
            bad.append((x['char'], x['engine_ink_before'], round(i, 3)))
    if bad:
        raise SystemExit('!! 这些记录窗里有**像字形的**墨, 拒绝覆盖: %s' % bad)
    if noise:
        for x in noise:
            print('[噪声] %s 的窗里原有 %d 个墨点 (与正确字形 IoU=%.3f, 只有正确字形的 %.0f%%) '
                  '⇒ 判为"非字形残渣", 覆盖掉:'
                  % (x['char'], x['engine_ink_before'], x['noise_iou'], 100 * x['noise_frac']))
            u0, v0, u1, v1 = x['rect']
            for row in A.eng[v0:v1, u0:u1]:
                print('        |' + ''.join('#' if v else '.' for v in row) + '|')
    else:
        print('[查  ] 6 个目标窗在引擎口径里都是全空的 ✓ (写进去不覆盖任何像素)')

    target = A.eng.copy()
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        target[v0:v1, u0:u1] = x['bitmap']
    ys, xs = np.where(target != A.eng)
    print('[计  ] 将写入 %d 个像素 (6 个 16x16 窗)' % len(ys))
    if a.dry_run:
        print('[dry ] 不写盘。')
        return 0

    empty_val, _hist = A.empty_index()
    hdr = A.headers()
    A.write_pixels(ys, xs, target[ys, xs], empty_val)
    for (doff, hb) in hdr:
        if bytes(A.cont[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) != hb:
            raise SystemExit('!! 48B 包头被动过 (doff=0x%X)' % doff)

    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(font['pak_e']['iso_off'] + A.px_off)
        f.write(bytes(A.cont))
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了'

    # ---- 回读 ----
    with open(dst, 'rb') as f:
        f.seek(font['pak_e']['iso_off'])
        pak2 = f.read(font['pak_e']['stored'])
    if bytes(pak2[:A.px_off]) != bytes(am['pak'][:A.px_off]) or \
       bytes(pak2[A.px_off + A.px_size:]) != bytes(am['pak'][A.px_off + A.px_size:]):
        raise SystemExit('!! 回读: COMMON.PAK 里像素容器以外的字节被改动了')
    A2 = repack_font.Atlas(pak2, A.px_off, A.px_size, A.w, A.h, A.psm)
    if not np.array_equal(A2.eng, target):
        raise SystemExit('!! 回读: 盘上解出的引擎图与目标图不一致 (%d 像素)'
                         % int((A2.eng != target).sum()))
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        if not np.array_equal(A2.eng[v0:v1, u0:u1], x['bitmap']):
            raise SystemExit('!! 回读: %s 的字形没写对' % x['char'])
    print('[验  ] 回读: 引擎图逐像素一致 ✓; 6 个字形的引擎采样窗 == 方正像素16 渲染 ✓')

    # ---- 用工程自己的 GlyphCache 复检 ----
    g2 = tcslib.GlyphCache(tcslib.Charset(), tcslib.Iso(dst))
    for x in targets:
        if not g2.has_glyph(x['char']):
            raise SystemExit('!! %s 仍然判"没有字形": %s' % (x['char'], g2.glyph_reason(x['char'])))
    print('[验  ] GlyphCache 复检: %s 全部"有字形" ✓'
          % ''.join(x['char'] for x in targets))

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
        src=rel(src), dst=rel(dst), grid_row=GRID_ROW, y=yrow(GRID_ROW),
        note='这 6 个单字节汉字的位图当年写在 flat 坐标, 引擎按引擎坐标采样 ⇒ 一直画不出来; '
             '本补丁把**同一张位图**写到引擎真正采样的记录窗里',
        source='third_party/fonts/方正像素16.ttf (render16 配方同 tools/font_pipeline/gen_font16.py)',
        cross_check='与 GR_ZH93 的 flat 原始位图逐像素比对',
        fixed=[dict(code='0x%02X' % x['code'], char=x['char'], rect=x['rect'],
                    ink=x['ink_ttf'], zh93_flat_ink=x.get('zh93_flat_ink'),
                    zh93_iou=x.get('zh93_iou'), engine_ink_before=x['engine_ink_before'],
                    overwritten_noise=(x.get('noise_iou') is not None))
               for x in targets],
        skipped=skipped, pixels_written=len(ys)), ensure_ascii=False, indent=1) + '\n')
    print('[rep ] → %s' % rel(REPORT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
