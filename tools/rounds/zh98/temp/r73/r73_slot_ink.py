"""r73_slot_ink.py -- for every legal slot 0..1503, measure ink in the engine cell.

Read-only. Tells us how many of the 1504 dual-byte slots actually have a glyph in the
shipping ISO, and where the missing ones are (this decides whether there is really zero
headroom, and whether "capacity" numbers in older reports are trustworthy).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D      # noqa: E402
import tcslib              # noqa: E402


def main():
    iso = sys.argv[1]
    g = D.load_font(iso)
    atlas = g['atlas']
    w, h = atlas['w'], atlas['h']
    gray = D.atlas_gray(atlas, 'engine')          # engine view (packet-aware)
    flat = D.atlas_gray(atlas, 'flat')            # old view (raw container)
    cs = tcslib.Charset()

    def ink(img, x, y, cw=tcslib.CW, ch=tcslib.CH):
        n = 0
        for yy in range(y, min(y + ch, h)):
            base = yy * w
            for xx in range(x, min(x + cw, w)):
                if img[base + xx] == 0:
                    n += 1
        return n

    used_slots = set()
    for ch_, (b1, b2) in cs.enc_pair.items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            used_slots.add(tcslib.pair_slot(b1, b2))

    n_eng = n_flat = n_none = 0
    empty_rows = {}
    for s in range(tcslib.pair_capacity()):
        row, col = s // tcslib.NCOL, s % tcslib.NCOL
        xe, ye = 16 * col, tcslib.GRID_Y0 + tcslib.CH * (
            row + (tcslib.GRID_SKIP_ROWS if row >= tcslib.GRID_SKIP_ROW else 0))
        ie = ink(gray, xe, ye)
        xf, yf = tcslib.atlas_flat_pos(xe, ye, w)
        iff = ink(flat, xf, yf)
        mark = ''
        if s not in used_slots:
            mark = ' [UNASSIGNED]'
        if ie == 0 and iff == 0:
            n_none += 1
            empty_rows.setdefault(row, []).append(col)
            mark += ' NO-INK-BOTH'
        elif ie > 0:
            n_eng += 1
        else:
            n_flat += 1
            mark += ' flat-only'
        if mark:
            print(f"slot {s:4d} row{row:2d} col{col:2d} eng=({xe},{ye}) ink={ie:3d} flat=({xf},{yf}) ink={iff:3d}{mark}")

    print()
    print(f"slots with ink in ENGINE cell : {n_eng}")
    print(f"slots with ink only in FLAT   : {n_flat}")
    print(f"slots with NO ink anywhere    : {n_none}")
    print(f"charset pair codes assigned   : {len(used_slots)}")
    print("rows with empty slots:", {k: len(v) for k, v in sorted(empty_rows.items())})


main()
