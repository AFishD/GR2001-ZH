# -*- coding: utf-8 -*-
r"""patch_zh51_single_byte_band.py — 修 28 个单字节汉字 (0x80..0x9C) 的**字形错位**。

## 症状 (round51 由 `tools/iso_build/single_cell_font.py` 穷举发现)

`FONT.RES` 的 default face 里有 28 条记录把**采样窗**指向图集底部 y=482 那条带::

    code 0x80..0x91, 0x93..0x9C   rec = (16*k, 482, 16*k+16, 498)   ← 28 个 16x16 窗

引擎按记录矩形采样 (round45 实机 A/B 已证: 记录矩形在哪, 字就在哪)。可是这 28 个窗里
**根本不是这 28 个字** —— 单格字库工具用 `方正像素16` 模板做**全盘搜索**, 每个字的字形
都**在图上找得到 (逐像素 0 差异)**, 但位置偏了:

    · 0x80..0x8B (12 个): 字形在 (x+256, y-1)  ← flat 容器坐标 (u0, 482) 的等价引擎位置
    · 0x8C..0x9C (16 个): 字形在 (x-192, y+1)  ← flat 容器坐标 (u0+576, 483) 的等价引擎位置

⇒ 这 28 个字**画出来全是别人的像素** (实机表现 = 那几页正文里出现别的字)。
成因: round43 的 `patch_zh93_font_ext_fix.py` 把新单字节码的字形写进了"底部空区", 但用的是
**flat 容器坐标** (当时以为引擎按 flat 采样), 而引擎按**引擎图**采样 ⇒ 一直错位。
round45/46 只订正了**对偶格**与**行 24 的 6 个记录码**, 这条带漏掉了。

## 本补丁做什么

1. 把 28 个字的**正确位图**写到**引擎真正采样的记录矩形**里 (u0,482)-(u0+16,498);
   位图来源 = `third_party/fonts/方正像素16.ttf` 按 `gen_font16.render16()` **同款配方**渲染;
2. 清掉旧错位字形**伸出采样窗之外**的孤儿像素 (第 481 行 / 第 498 行) —— 只清
   "不属于任何采样窗"的像素, 一个活字形都不碰;
3. 写盘走 `repack_font.Atlas` (GIF 封包换算, **绝不碰 48B 包头**), 回读逐像素复核。

## 安全性断言 (写盘前全部先过)

* 28 个记录窗**铺满** x=0..447 × y=482..497, 两两不重叠;
* 除了这 28 个窗, **没有任何**采样窗 (三个 face 的全部 FT 记录矩形 ∪ 全部在用对偶格)
  与 y=481..498 × x=0..447 相交 ⇒ 改写这里不会碰到别人的字形;
* 改动像素必须全部落在 y=481..498 × x=0..447 之内;
* 只改 `COMMON.PAK` 里 `new_font_revised` 的**像素数据区**; `FONT.RES` / IMG 条目表 /
  ELF / PVD / PAK 包头**一个字节都不动**。

用法:
  python tools/iso_build/patch_zh51_single_byte_band.py <src.iso> <dst.iso> [--dry-run]
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
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
import dump_font                                                         # noqa: E402
import repack_font                                                       # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
BAND_V0 = 482                     # 出问题的那条带 (记录 v0)
TOUCH = (478, 512, 0, 448)        # 允许改动的区域 (y0, y1, x0, x1)
CODE_LO, CODE_HI = 0x80, 0x9C     # 目标码位区间
CODE_SKIP = (0x92,)               # 0x92 若 的记录在别处 (ASCII 带), 不动


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def render16(ch):
    """与 tools/font_pipeline/gen_font16.py::render16 同款配方。"""
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    out = a[8:24, 8:24] < 128
    if not out.any():
        raise SystemExit('!! 方正像素16 渲染不出 %r' % ch)
    oy, ox = np.where(a < 128)
    if oy.min() < 8 or ox.min() < 8 or oy.max() >= 24 or ox.max() >= 24:
        raise SystemExit('!! %r 的墨越出 16x16 em 窗' % ch)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=None)
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    print('=' * 78)
    print('修 28 个单字节汉字 (0x%02X..0x%02X) 的字形错位 —— 写到引擎真正采样的记录窗'
          % (CODE_LO, CODE_HI))
    print('  src = %s' % rel(src))
    print('=' * 78)

    font = dump_font.load_font(src)
    am = font['atlas']
    faces = font['faces']
    W, H = am['w'], am['h']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], W, H, am['psm'])
    cs = tcslib.Charset()
    recs = [x for x in faces if x[0] == 'default'][0][2]

    # ---- ① 目标清单 ----
    targets, skipped = [], []
    for idx, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        code = idx + 0x20
        if v0 != BAND_V0 or u1 <= u0 or v1 <= v0:
            continue
        if not (CODE_LO <= code <= CODE_HI) or code in CODE_SKIP:
            skipped.append(dict(code=code, rect=[u0, v0, u1, v1], why='不在目标区间'))
            continue
        ch = cs.codes.get(code)
        if ch is None:
            skipped.append(dict(code=code, rect=[u0, v0, u1, v1],
                                why='该字节现在没有映射 ⇒ 记录休眠, 不动'))
            continue
        if (u1 - u0, v1 - v0) != (tcslib.CW, tcslib.CH):
            skipped.append(dict(code=code, rect=[u0, v0, u1, v1],
                                why='记录不是 16x16 (%dx%d)' % (u1 - u0, v1 - v0)))
            continue
        targets.append(dict(code=code, char=ch, rect=[u0, v0, u1, v1],
                            bitmap=render16(ch)))
    print('[找  ] y=%d 的记录: 目标 %d 条, 跳过 %d 条' % (BAND_V0, len(targets), len(skipped)))
    for x in skipped:
        print('       skip 0x%02X %s — %s' % (x['code'], x['rect'], x['why']))
    if not targets:
        raise SystemExit('!! 没有目标 —— 这张盘不需要本补丁 (或已经修过)')

    # ---- ② 安全性断言: 目标窗铺满且无重叠; 别的采样窗不碰这一带 ----
    cover = np.zeros((H, W), bool)
    for (nm, _fld, rs) in faces:
        for (b0, b1, u0, v0, u1, v1) in rs:
            if u1 > u0 and v1 > v0:
                cover[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
    for (_b1, _b2) in cs.enc_pair.values():
        if not (tcslib.PAIR_LEAD_LO <= _b1 < tcslib.PAIR_LEAD_HI):
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(_b1, _b2))
        cover[max(0, y):min(H, y + 16), max(0, x):min(W, x + 16)] = True

    tgt_mask = np.zeros((H, W), bool)
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        tgt_mask[v0:v1, u0:u1] = True
    dup = int(tgt_mask.sum()) - sum(tcslib.CW * tcslib.CH for _ in targets)
    assert dup == 0, '!! 目标记录窗互相重叠 (%d px)' % dup

    other = cover & ~tgt_mask
    y0, y1, x0, x1 = TOUCH
    zone = np.zeros((H, W), bool)
    zone[y0:y1, x0:x1] = True
    intr = int((other & zone).sum())
    print('[查  ] 目标窗 %d 个铺满 %d px; 该区域内**别人的采样窗** %d px'
          % (len(targets), int(tgt_mask.sum()), intr))
    if intr:
        raise SystemExit('!! 这一带还有别的采样窗 (%d px) —— 拒绝改写 (会碰坏别人的字形)' % intr)

    # ---- ③ 目标图 ----
    eng = A.eng
    target = eng.copy()
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        x['ink_before'] = int(eng[v0:v1, u0:u1].sum())
        x['ink_ttf'] = int(x['bitmap'].sum())
        target[v0:v1, u0:u1] = x['bitmap']
    # 孤儿: 旧错位字形伸出采样窗的像素 (y=481 / y=498) ⇒ 清掉, 免得变成残墨
    orphan = target & ~cover & zone
    n_orphan = int(orphan.sum())
    target[orphan] = False
    print('[清  ] 旧错位字形伸到窗外的孤儿像素 %d 个 (第 481/498 行) ⇒ 清掉' % n_orphan)

    ys, xs = np.where(target != eng)
    print('[计  ] 将改 %d 个像素' % len(ys))
    if len(ys):
        assert ys.min() >= TOUCH[0] and ys.max() < TOUCH[1], '改动越出授权行范围'
        assert xs.min() >= TOUCH[2] and xs.max() < TOUCH[3], '改动越出授权列范围'
    if a.dry_run:
        print('[dry ] 不写盘。')
        return 0

    # ---- ④ 写盘 (只碰像素数据区) ----
    empty_val, _hist = A.empty_index()
    hdr_before = A.headers()
    A.write_pixels(ys, xs, target[ys, xs], empty_val)
    for (doff, hb) in hdr_before:
        if bytes(A.cont[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) != hb:
            raise SystemExit('!! 有 48B 包头被改了 (doff=0x%X)' % doff)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(font['pak_e']['iso_off'] + A.px_off)
        f.write(bytes(A.cont))
    assert os.path.getsize(src) == os.path.getsize(dst), '!! ISO 尺寸变了'

    # ---- ⑤ 回读复核 ----
    with open(dst, 'rb') as f:
        f.seek(font['pak_e']['iso_off'])
        pak2 = f.read(font['pak_e']['stored'])
    if bytes(pak2[:A.px_off]) != bytes(am['pak'][:A.px_off]) or \
       bytes(pak2[A.px_off + A.px_size:]) != bytes(am['pak'][A.px_off + A.px_size:]):
        raise SystemExit('!! 回读: COMMON.PAK 里像素容器以外的字节被改动了')
    A2 = repack_font.Atlas(pak2, A.px_off, A.px_size, W, H, A.psm)
    if not np.array_equal(A2.eng, target):
        raise SystemExit('!! 回读: 引擎图不一致 (%d px)' % int((A2.eng != target).sum()))
    for x in targets:
        u0, v0, u1, v1 = x['rect']
        if not np.array_equal(A2.eng[v0:v1, u0:u1], x['bitmap']):
            raise SystemExit('!! 回读: %s 的字形没写对' % x['char'])
    left = int((A2.eng & ~cover & zone).sum())
    print('[验  ] 回读: 引擎图逐像素一致 ✓; 28 个采样窗 == 方正像素16 渲染 ✓; '
          '带内孤儿墨 %d ✓' % left)
    if left:
        raise SystemExit('!! 带内还有孤儿墨 %d' % left)

    # ---- ⑥ 用工程自己的 GlyphCache 复检 ----
    g2 = tcslib.GlyphCache(tcslib.Charset(), tcslib.Iso(dst))
    bad = [x['char'] for x in targets if not g2.has_glyph(x['char'])]
    if bad:
        raise SystemExit('!! 这些字仍判"没有字形": %s' % ''.join(bad))
    print('[验  ] GlyphCache 复检: %d 个字全部"有字形" ✓' % len(targets))

    rep = dict(src=rel(src), dst=rel(dst), tool='tools/iso_build/patch_zh51_single_byte_band.py',
               band_v0=BAND_V0, codes='0x%02X..0x%02X (除 %s)'
               % (CODE_LO, CODE_HI, ','.join('0x%02X' % c for c in CODE_SKIP)),
               n_fixed=len(targets), pixels_written=len(ys), orphans_cleared=n_orphan,
               source='third_party/fonts/方正像素16.ttf (render16 配方同 tools/font_pipeline/gen_font16.py)',
               why='这 28 个单字节汉字的字形当年被写在 **flat 容器坐标**, 而引擎按**引擎图**采样 '
                   '⇒ 记录窗里是别人的像素; 本补丁把同一张位图写到引擎真正采样的位置',
               fixed=[dict(code='0x%02X' % x['code'], char=x['char'], rect=x['rect'],
                           ink_before=x['ink_before'], ink=x['ink_ttf']) for x in targets],
               skipped=skipped, iso_sha256_after=tcslib.sha256_file(dst))
    rp = a.report or os.path.join(os.path.dirname(os.path.abspath(dst)), 'temp',
                                  'single_byte_band_fix.json')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    io.open(rp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print('[报告] %s' % rel(rp))
    print('[完成] %s  sha256=%s' % (rel(dst), rep['iso_sha256_after']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
