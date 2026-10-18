# -*- coding: utf-8 -*-
r"""zx_r84_tri.py — round84：**△ 修复**（Lead 批准，零风险）

    python tools/re/toolbelt/zx_r84_tri.py <src.iso> <dst.iso> [--dry-run]

槽 1504（对偶码 0xB1 0xA1）现在是上一轮**手绘**的 16×16 空心三角，
`dump_font` 的"字形几何体检"把它列为**唯一 1 个错误**。
本补丁把它的像素换成 `third_party/fonts/方正像素16.ttf` 渲染的 △。

只改：`new_font_revised` 容器里槽 1504 那 16×16 的像素（nibble 级）
不动：h / px_size / 容器尺寸 / PAK 长度 / ELF / charset / 文本 / FONT.RES / MENU 条目表
"""
import argparse
import io
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np          # noqa: E402
import tcslib               # noqa: E402
import zx_lib               # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r84')
os.makedirs(OUT, exist_ok=True)
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
SLOT = 1504
CH = '△'
W, H = 1024, 512
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def render16(ch):
    """FZXS16 16px → 16x16 布尔墨窗（draw origin (8,8)，窗 = canvas[8:24,8:24) = em）。"""
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    out = a[8:24, 8:24] < 128
    full = a < 128
    fys, fxs = np.where(full)
    assert fys.min() >= 8 and fxs.min() >= 8 and fys.max() < 24 and fxs.max() < 24, \
        '墨越出 16x16 em 窗: %r' % ch
    return out


class Pix:
    """引擎口径 (x,y) ↔ 容器字节（就地 nibble 读写）。"""

    def __init__(self, cont, w=W):
        self.cont = bytearray(cont)
        self.rows = {fr: (doff, nb) for (fr, doff, nb) in zx_lib.seg_table(self.cont, w)}

    def off(self, x, y):
        best = None
        for fr, (doff, nb) in self.rows.items():
            d = y - fr
            if 0 <= d * (W // 2) + x // 2 < nb:
                best = doff + d * (W // 2) + x // 2
        assert best is not None, '像素越界/未覆盖 (%d,%d)' % (x, y)
        return best

    def get(self, x, y):
        b = self.cont[self.off(x, y)]
        return ((b >> 4) if (x & 1) else (b & 0x0F)) == 0

    def set(self, x, y, ink, empty=1):
        o = self.off(x, y)
        cur = self.cont[o]
        v = 0 if ink else empty
        self.cont[o] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)

    def window(self, x0, y0, w, h):
        g = np.zeros((h, w), dtype=bool)
        for y in range(h):
            for x in range(w):
                g[y, x] = self.get(x0 + x, y0 + y)
        return g

    def blit(self, bmp, x0, y0):
        h, w = bmp.shape
        for y in range(h):
            for x in range(w):
                self.set(x0 + x, y0 + y, bool(bmp[y, x]))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=os.path.join(OUT, 'tri_report.json'))
    a = ap.parse_args(argv)
    P('=' * 78)
    P('zx_r84_tri.py  △ 修复（槽 %d ← render16(%s, %r)）' % (SLOT, os.path.basename(FZ16), CH))
    P('  src = %s' % a.src)
    P('  dst = %s' % (a.dst or '(dry-run)'))
    P('=' * 78)

    iso = tcslib.Iso(a.src)
    names = []
    for i in range(2000):
        e = iso.img_entry(zx_lib.MENU_LBA, i)
        if e['name'].startswith('?'):
            break
        names.append(e['name'])
    e_pak = iso.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
    names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
    hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
    pak = bytearray(iso.read(e_pak['iso_off'], e_pak['stored']))
    iso.close()
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 400659)

    recs = tcslib.parse_pak_records(bytes(pak))
    nm, psm, w, h, clut, px_size, PX = recs[1]
    assert (nm, psm, w, h, px_size) == ('new_font_revised', 0x14, W, H, 0x40010)
    old_ct = bytes(pak[PX:PX + px_size])

    # 槽 1504 的格子坐标（现役公式: ncol=62, y0=2, row>=12 加 3）
    x, y = tcslib.atlas_cell_xy_engine_view(SLOT)
    P('[slot] slot=%d -> (x,y)=(%d,%d)  16x16' % (SLOT, x, y))
    assert (x, y) == (16 * (SLOT % 62),
                      2 + 16 * (SLOT // 62 + (3 if SLOT // 62 >= 12 else 0)))

    pix = Pix(old_ct)
    before = pix.window(x, y, 16, 16)
    tpl = render16(CH)
    P('[glyph] 旧（手绘三角）墨 = %d ; 新（模板 △）墨 = %d ; 相同 = %s'
      % (int(before.sum()), int(tpl.sum()), bool((before == tpl).all())))
    if (before == tpl).all():
        P('[skip] 已经一致，无需改动')
        return 0

    pix.blit(tpl, x, y)
    new_ct = bytes(pix.cont)

    # ── 断言 ──
    pix2 = Pix(new_ct)
    after = pix2.window(x, y, 16, 16)
    assert (after == tpl).all(), '槽 %d 回读 != 模板' % SLOT
    P('[A1] 槽 %d 回读逐 texel == 模板 ✓' % SLOT)
    # 其它现役格位完全不动
    diff = [i for i in range(len(old_ct)) if old_ct[i] != new_ct[i]]
    P('[A2] 容器差异字节 %d 个（应只落在槽 %d 的 16x16 = 128 B 里）' % (len(diff), SLOT))
    lo, hi = min(diff), max(diff)
    P('     差异范围 0x%X..0x%X' % (lo, hi))
    nbad = 0
    for s in range(1736):
        if s == SLOT:
            continue
        cx, cy = tcslib.atlas_cell_xy_engine_view(s)
        if not (pix.window(cx, cy, 16, 16) == pix2.window(cx, cy, 16, 16)).all():
            nbad += 1
    P('[A3] 其余 1735 个现役格位逐 texel 不变: %s（不同 %d 个）'
      % ('✓' if nbad == 0 else '✗', nbad))
    assert nbad == 0
    # 容器尺寸 / PAK 长度 / 记录字段
    new_pak = bytearray(bytes(pak))
    new_pak[PX:PX + px_size] = new_ct
    assert len(new_pak) == len(pak)
    rr = tcslib.parse_pak_records(bytes(new_pak))
    P('[A4] PAK 长度 %d == %d ✓ ; 记录 %s psm=0x%X %dx%d px_size=0x%X ✓'
      % (len(new_pak), len(pak), rr[1][0], rr[1][1], rr[1][2], rr[1][3], rr[1][5]))

    if a.dry_run:
        P('[dry-run] 不写盘')
        _save(a, dict(dry=True, slot=SLOT, ink_old=int(before.sum()), ink_new=int(tpl.sum()),
                      diff_bytes=len(diff)))
        return 0

    # ── 写盘（原盘逐字节拷贝，只改容器）──
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    with open(a.src, 'rb') as fi, open(a.dst, 'wb') as fo:
        while True:
            blk = fi.read(1 << 22)
            if not blk:
                break
            fo.write(blk)
    base = zx_lib.MENU_LBA * 2048
    with open(a.dst, 'r+b') as f:
        f.seek(base + e_pak['off'] + PX)
        f.write(new_ct)
    iso2 = tcslib.Iso(a.dst)
    assert zx_lib.names_region(iso2, zx_lib.MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, zx_lib.MENU_LBA) == hash0
    assert zx_lib.header(iso2, zx_lib.MENU_LBA)['raw'] == hdr['raw']
    pak2 = bytes(iso2.read(e_pak['iso_off'], e_pak['stored']))
    P('[A5] 回读 PAK 长度 %d ✓ ; vs 新容器差异 %d B'
      % (len(pak2), sum(1 for i in range(len(pak2)) if pak2[i] != new_pak[i])))
    assert pak2 == bytes(new_pak)
    ct2 = pak2[PX:PX + px_size]
    pix3 = Pix(ct2)
    assert (pix3.window(x, y, 16, 16) == tpl).all()
    P('[A6] 回读槽 %d == 模板 ✓' % SLOT)
    P('[A7] ELF 未改 / 名字区 + 4096 槽哈希表 + MENU 头 逐字节不变 ✓')
    P('[A8] ISO 尺寸 %d == %d ✓' % (os.path.getsize(a.dst), os.path.getsize(a.src)))
    assert os.path.getsize(a.dst) == os.path.getsize(a.src)
    iso2.close()
    _save(a, dict(dry=False, slot=SLOT, ink_old=int(before.sum()), ink_new=int(tpl.sum()),
                  diff_bytes=len(diff)))
    return 0


def _save(a, extra):
    with io.open(a.report, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=extra, log=LOG), f, ensure_ascii=False, indent=1)
    P('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
