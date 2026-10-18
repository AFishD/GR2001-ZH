# -*- coding: utf-8 -*-
r"""patch_zh52_residue.py — round52: **清真残墨**（用户点名："dump 的字库还有一小部分没有清空"）

## 现象（用户看到的）
字库贴图左下角有一块"上下三角混合"的乱码；`稳` 右侧、末列右侧也有零星墨点。

## 逻辑漏洞（round49 判据的假阴性）
round49 `font_residue.py` 的判据是

    残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录窗, **膨胀 ±(4,2)**)

那个 ±(4,2) 是 round44~46 时代（还没搞清"引擎按记录矩形原样采样"之前）留下的**保守余量**，
后果是：**紧贴记录矩形、但根本不属于任何字形的墨点被"保护"下来了** ⇒ 工具报"残墨 0"，
人眼却能看到。round51 已经证明"引擎按 FT 记录矩形**原样**采样"（写进矩形 ⇒ 逐像素等于模板），
所以这个余量可以取消。

## 本补丁的判据（严格口径）

    残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录矩形, **原样, 0 余量**)

⇒ 在 GR_ZH101 上量得 **167 px / 39 个团块**（其中 18 px 就在 `稳` 右侧 2px 处）。

## 安全性
- 只写**像素容器数据区**（`Atlas` 封包感知写入），48 B 包头逐字节不动；
- 写前硬断言：改动像素必须全部落在"非已用格 ∧ 非记录矩形"内；
- 写后回读：残留必须为 **0**；已用格/记录矩形内的像素**一个都不许变**。

用法:
  python tools/iso_build/patch_zh52_residue.py <src.iso> <dst.iso> [--dry-run]
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

import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402
from patch_zh94_glyph_align import Atlas                # noqa: E402

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')


def build_masks(iso):
    w = D.load_font(iso)
    ad, faces = w['atlas'], w['faces']
    W, H = ad['w'], ad['h']
    g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
    ink = g < 128
    cs = json.load(io.open(CHARSET, encoding='utf-8'))

    used = np.zeros((H, W), dtype=bool)
    n_used = 0
    for ch, (b1, b2) in cs['pair_of'].items():
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
        if 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H:
            used[y:y + 16, x:x + 16] = True
            n_used += 1
    ft = np.zeros((H, W), dtype=bool)
    n_rec = 0
    for _f, _fld, rs in faces:
        for r in rs:
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            ft[v0:v1, u0:u1] = True
            n_rec += 1
    return dict(w=w, ad=ad, W=W, H=H, g=g, ink=ink, used=used, ft=ft,
                residue=ink & ~used & ~ft, n_used=n_used, n_rec=n_rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    M = build_masks(a.src)
    ink, used, ft, resid = M['ink'], M['used'], M['ft'], M['residue']
    print('[量] 墨 %d px = 已用对偶格内 %d + FT 记录内 %d + **残留 %d** (已用格 %d / 记录 %d 条)'
          % (int(ink.sum()), int((ink & used).sum()), int((ink & ft & ~used).sum()),
             int(resid.sum()), M['n_used'], M['n_rec']))
    ys, xs = np.nonzero(resid)
    if len(ys) == 0:
        print('[done] 无残留 (幂等)')
        return 0
    print('[量] 残留 bbox x%d..%d y%d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
    if a.dry_run or not a.dst:
        print('[dry ] 未写盘')
        return 0

    ad = M['ad']
    A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
    En, _c = A.decode_engine()
    # 硬断言: 要清的像素一个都不许落在"已用格/记录矩形"里
    assert not (resid & (used | ft)).any(), '待清像素落在保护区内'
    before_prot = En[used | ft].copy()
    for y, x in zip(ys.tolist(), xs.tolist()):
        A.set_px(int(x), int(y), False, 1)
    back, _c2 = A.decode_engine()
    assert (back[used | ft] == before_prot).all(), '保护区像素被改动了'
    n_changed = int((back != En).sum())
    print('[写] 清掉 %d 像素 (回读确认改动 %d px)' % (len(ys), n_changed))

    shutil.copyfile(a.src, a.dst)
    with open(a.dst, 'r+b') as f:
        f.seek(M['w']['pak_e']['iso_off'] + ad['px_off'])
        f.write(bytes(A.nib))
    assert os.path.getsize(a.src) == os.path.getsize(a.dst)

    # 回读验收: 残留必须 0
    M2 = build_masks(a.dst)
    r2 = int(M2['residue'].sum())
    ink2 = int(M2['ink'].sum())
    print('[验] 回读: 墨 %d (原 %d, 差 %d) ; **残留 %d** %s'
          % (ink2, int(ink.sum()), int(ink.sum()) - ink2, r2, '✓' if r2 == 0 else '✗'))
    # 已用格 / 记录矩形内的墨必须一个不少
    lost = int((ink & used & ~M2['ink']).sum()) + int((ink & ft & ~used & ~M2['ink']).sum())
    print('[验] 已用格+记录矩形内丢失的墨: %d %s' % (lost, '✓' if lost == 0 else '✗'))
    return 0 if (r2 == 0 and lost == 0) else 3


if __name__ == '__main__':
    sys.exit(main())
