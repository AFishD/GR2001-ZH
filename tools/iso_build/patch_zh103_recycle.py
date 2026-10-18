# -*- coding: utf-8 -*-
r"""patch_zh103_recycle.py — round53: **回收没人要的旧墨**（用户："回收所有没使用的字的格子"）

## 判据（round52 的"严格口径"还不够，要再看**墨归谁**）

round52 的 `patch_zh52_residue.py` 用

    可清 = 墨 ∧ ¬(在用对偶格) ∧ ¬(全部 FT 记录矩形)

⇒ 它会把**非活记录**（码位引擎根本不会画）占着的旧墨也一起保护下来。
本补丁把保护罩收窄到**活**记录：

    活记录 = ① 我们的单字节码**且正文里真出现过**（0 次出现的不算活）
             ② 可打印 ASCII 0x20..0x7E
             ③ 引擎硬编码: 0x7B/0x7D 滚动箭头、0xB1/0xB5 图标码记录槽

    可回收 = 墨 ∧ ¬(在用对偶格) ∧ ¬(活 FT 记录矩形)

GR_ZH102 实测: 可回收 **123 px**，清掉后 **2 个槽位**(slot 683/684, row11 col1/col2)
从"压着旧墨"变成**可用格**（可用格 239 → 241）。

## 安全性
- 封包感知写入（`Atlas`），48 B 包头逐字节不动；
- 写前硬断言：待清像素必须全落在"非在用格 ∧ 非活记录矩形"内；
- 写后回读：可回收墨必须为 0；**在用格 + 活记录矩形内的墨一个都不许变**。

用法:
  python tools/iso_build/patch_zh103_recycle.py <src.iso> <dst.iso> [--dry-run]
"""
import argparse
import csv
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
KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}


def analyse(iso, textdir=None):
    w = D.load_font(iso)
    ad, faces = w['atlas'], w['faces']
    W, H = ad['w'], ad['h']
    g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
    ink = g < 128
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}

    occ = {}
    td = textdir or os.path.join(os.path.dirname(os.path.abspath(iso)), 'text')
    if not os.path.isdir(td):
        raise SystemExit('!! 找不到文本表目录 %s —— 没有它就无法判断"哪些字真被用到", '
                         '绝不能凭猜测清墨 (round53 教训)' % td)
    for fn in os.listdir(td):
        if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
            with io.open(os.path.join(td, fn), encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    for ch in (row.get('text_edited') or ''):
                        occ[ch] = occ.get(ch, 0) + 1
    if not occ:
        raise SystemExit('!! 文本表读出来是空的 (%s) —— 中止, 否则会把活字形当垃圾清掉' % td)

    def is_live(code):
        if code in KEEP_HARD or 0x20 <= code <= 0x7E:
            return True
        if code in code2ch:
            return occ.get(code2ch[code], 0) > 0
        return False

    rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
    live = np.zeros((H, W), dtype=bool)
    n_live = n_dead = 0
    for idx, r in enumerate(rec):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            continue
        if is_live(idx + 0x20):
            live[v0:v1, u0:u1] = True
            n_live += 1
        else:
            n_dead += 1

    used = np.zeros((H, W), dtype=bool)
    n_used = 0
    for ch, (b1, b2) in cs['pair_of'].items():
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
        if 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H:
            used[y:y + 16, x:x + 16] = True
            n_used += 1
    return dict(w=w, ad=ad, W=W, H=H, ink=ink, used=used, live=live,
                recycle=ink & ~used & ~live, n_used=n_used, n_live=n_live, n_dead=n_dead)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--text', default=None)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    M = analyse(a.src, a.text)
    # 文本表目录只解析一次, 回读校验复用同一个 (输出盘旁边通常没有 text/)
    td_used = a.text or os.path.join(os.path.dirname(os.path.abspath(a.src)), 'text')
    ink, used, live, rec = M['ink'], M['used'], M['live'], M['recycle']
    print('[量] 图集墨 %d px = 在用格内 %d + 活记录内 %d + **可回收 %d** (活记录 %d 条 / 非活 %d 条)'
          % (int(ink.sum()), int((ink & used).sum()), int((ink & live & ~used).sum()),
             int(rec.sum()), M['n_live'], M['n_dead']))
    ys, xs = np.nonzero(rec)
    if len(ys) == 0:
        print('[done] 没有可回收的墨 (幂等)')
        return 0
    print('[量] 可回收 bbox x%d..%d y%d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
    if a.dry_run or not a.dst:
        print('[dry ] 未写盘')
        return 0

    ad = M['ad']
    A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
    En, _c = A.decode_engine()
    assert not (rec & (used | live)).any(), '待清像素落在保护区内'
    before = En[used | live].copy()
    for y, x in zip(ys.tolist(), xs.tolist()):
        A.set_px(int(x), int(y), False, 1)
    back, _c2 = A.decode_engine()
    assert (back[used | live] == before).all(), '保护区像素被改动'
    print('[写] 回收 %d 像素 (回读确认改动 %d px)' % (len(ys), int((back != En).sum())))

    shutil.copyfile(a.src, a.dst)
    with open(a.dst, 'r+b') as f:
        f.seek(M['w']['pak_e']['iso_off'] + ad['px_off'])
        f.write(bytes(A.nib))
    assert os.path.getsize(a.src) == os.path.getsize(a.dst)

    M2 = analyse(a.dst, td_used)
    r2 = int(M2['recycle'].sum())
    lost = int((ink & (used | live) & ~M2['ink']).sum())
    print('[验] 回读: 可回收 %d %s ; 保护区丢失的墨 %d %s'
          % (r2, '✓' if r2 == 0 else '✗', lost, '✓' if lost == 0 else '✗'))
    return 0 if (r2 == 0 and lost == 0) else 3


if __name__ == '__main__':
    sys.exit(main())
