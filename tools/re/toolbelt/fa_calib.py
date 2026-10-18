# -*- coding: utf-8 -*-
r"""fa_calib.py — 采样窗口径**暴力反解**（只读）

    python tools/re/toolbelt/fa_calib.py --iso <iso> --codes B2,B3,B4,B6,B7,B8,B9,41,42

对每个码: 取 FT 记录 (idx=code-0x20, large face) 的原始 (u0,v0,u1,v1) 16x16 窗,
在整张图集引擎像素面上**穷举所有 16x16 窗 (x,y 步长 2)** 找逐 texel 相等的那些位置。
⇒ 由此得出该盘的「记录窗 → 图集格」真实映射 (是否带偏移/相位), 不靠猜。
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


def ink_plane(plane, w, h):
    a = np.frombuffer(plane, dtype=np.uint8).reshape(h, w // 2)
    g = np.zeros((h, w), dtype=bool)
    g[:, 0::2] = (a & 0x0F) == 0
    g[:, 1::2] = (a >> 4) == 0
    return g


def find_cells(G, win, step=2, maxhits=24):
    h, w = G.shape
    wh, ww = win.shape
    hits = []
    for y in range(0, h - wh + 1, step):
        for x in range(0, w - ww + 1, step):
            if np.array_equal(G[y:y + wh, x:x + ww], win):
                hits.append((x, y))
                if len(hits) >= maxhits:
                    return hits
    return hits


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--codes', default='B2,B3,B4,B6,B7,B8,B9')
    ap.add_argument('--face', default='large')
    ap.add_argument('--tag', default=None)
    ap.add_argument('--step', type=int, default=2)
    a = ap.parse_args(argv)
    tag = a.tag or os.path.splitext(os.path.basename(a.iso))[0]
    F = R.read_font(a.iso)
    G = ink_plane(F['plane'], F['w'], F['h'])
    R.P('=' * 92)
    R.P('fa_calib.py  iso=%s  %dx%d  face=%s' % (a.iso, F['w'], F['h'], a.face))
    R.P('=' * 92)
    face = [f for f in F['faces'] if f[0] == a.face][0]
    nm, fld, rows = face
    out = {}
    for tok in a.codes.split(','):
        code = int(tok, 16)
        idx = code - 0x20
        if idx >= len(rows):
            R.P('0x%02X idx=%d 越界' % (code, idx))
            continue
        _o, r = rows[idx]
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        if not (u1 > u0 and v1 > v0):
            R.P('0x%02X idx=%d 空记录 (%d,%d)-(%d,%d)' % (code, idx, u0, v0, u1, v1))
            out['0x%02X' % code] = dict(idx=idx, rect=[u0, v0, u1, v1], hits=[])
            continue
        win = G[v0:v1, u0:u1]
        hits = find_cells(G, win, step=a.step)
        R.P('0x%02X idx=%3d rec=(%3d,%3d)-(%3d,%3d) %2dx%-2d 墨=%3d ⇒ 全图逐 texel 相同位置 %d 个: %s'
          % (code, idx, u0, v0, u1, v1, u1 - u0, v1 - v0, int(win.sum()), len(hits),
             hits if len(hits) <= 12 else hits[:12]))
        out['0x%02X' % code] = dict(idx=idx, rect=[u0, v0, u1, v1], ink=int(win.sum()),
                                    hits=hits)
    with io.open(os.path.join(OUT, 'calib_%s.json' % tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    R.P('[out] %s' % os.path.join(OUT, 'calib_%s.json' % tag))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
