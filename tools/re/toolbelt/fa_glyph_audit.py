# -*- coding: utf-8 -*-
r"""fa_glyph_audit.py — ★ 各盘「槽段 → 墨」审计（只读）

回答: 现役 charset 的 1872 个 pair 落在 slot 0..1871（0 缺口）。各盘图集里这些槽到底有没有字形？
      特别关注 1736..1871（r84 的 136 个字）—— cap_build 把 1736..2349 写成探针图案了。

    python tools/re/toolbelt/fa_glyph_audit.py --iso <iso> --ncol 62 --tag zh124
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
import fa_recon as R                                                   # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--ncols', default='62,64')
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    F = R.read_font(a.iso)
    R.P('=' * 96)
    R.P('fa_glyph_audit.py  %s  %dx%d px_size=0x%X' % (a.iso, F['w'], F['h'], F['px_size']))
    R.P('=' * 96)
    plane, w, h = F['plane'], F['w'], F['h']

    cs = T.Charset()
    pairs = {ch: tuple(v) for ch, v in cs.enc_pair.items()}
    slot_char = {}
    for ch, pr in pairs.items():
        s = (pr[0] - 0xA1) * 94 + (pr[1] - 0xA1)
        slot_char.setdefault(s, []).append(ch)

    def rowfig(ncol):
        nrow = 0
        while 2 + 16 * (nrow + (3 if nrow >= 12 else 0)) + 16 <= h:
            nrow += 1
        return nrow, nrow * ncol

    rep = dict(iso=a.iso, w=w, h=h, px_size=F['px_size'], ncol={})
    for ncol in [int(x) for x in a.ncols.split(',')]:
        nrow, cap = rowfig(ncol)
        segs = []
        for (lo, hi, label) in ((0, 1503, '现役 r82'), (1504, 1735, 'r83 232'),
                                (1736, 1785, 'r84 前50 (lead B3 tail)'),
                                (1786, 1871, 'r84 后86 (lead B4)'),
                                (1872, 2344, '保留空'), (2345, 2349, '本轮借用 5'),
                                (2350, cap - 1, '余量')):
            n = nempty = nout = 0
            inks = []
            for s in range(lo, hi + 1):
                if s >= cap:
                    nout += 1
                    continue
                cx, cy = R.cell(s, ncol)
                if cy + 16 > h or cx + 16 > w:
                    nout += 1
                    continue
                g = R.window(plane, w, cx, cy, 16, 16)
                k = int(g.sum())
                n += 1
                if k == 0:
                    nempty += 1
                else:
                    inks.append(k)
            segs.append(dict(lo=lo, hi=hi, label=label, in_range=n, empty=nempty,
                             out_of_range=nout,
                             ink_min=(min(inks) if inks else None),
                             ink_max=(max(inks) if inks else None)))
            R.P('  ncol=%-3d 行 0..%-2d 容量 %-5d | 槽 %4d..%-4d %-26s 可寻址 %-5d 空 %-5d 越界 %-4d 墨[%s..%s]'
              % (ncol, nrow - 1, cap, lo, hi, label, n, nempty, nout,
                 min(inks) if inks else '-', max(inks) if inks else '-'))
        rep['ncol'][str(ncol)] = dict(nrow=nrow, cap=cap, segs=segs)
        # 逐槽明细 (前 40 个空槽)
        emp = []
        for s in range(0, min(cap, 2350)):
            cx, cy = R.cell(s, ncol)
            if cy + 16 > h or cx + 16 > w:
                continue
            if int(R.window(plane, w, cx, cy, 16, 16).sum()) == 0:
                emp.append(s)
        R.P('  ncol=%-3d ★ 空槽 %d 个 ; 前 40 个: %s' % (ncol, len(emp), emp[:40]))
        rep['ncol'][str(ncol)]['empty_slots'] = emp
    with io.open(os.path.join(OUT, 'glyphaudit_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    R.P('[out] %s' % os.path.join(OUT, 'glyphaudit_%s.json' % a.tag))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
