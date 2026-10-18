"""r73_capacity.py -- read-only capacity census of the SHIPPING font atlas.

Answers, with disk facts only (no emulator):
  * what the PAK record declares (psm/w/h/px_size) and the GIF TRXPOS segment list
  * FONT.RES face table: face count, per-face nrec = fld[4]*fld[5], base char, etc.
  * how many 16x16 cells the *grid* formula can address in the current atlas
  * how many cells each candidate lever would add

Usage: python r73_capacity.py <iso> [out.json]
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D          # noqa: E402
import tcslib                  # noqa: E402


def grid_yrow(r):
    """Engine grid row -> top texel y (identical to the ELF cave arithmetic)."""
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def usable_grid_rows(h):
    """Grid rows whose full 16x16 cell fits inside a texture of height h."""
    out = []
    for r in range(256):
        y = grid_yrow(r)
        if y + tcslib.CH > h:
            break
        out.append((r, y))
    return out


def main():
    iso = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    g = D.load_font(iso)
    atlas = g['atlas']
    faces = g['faces']
    w, h, psm = atlas['w'], atlas['h'], atlas['psm']

    rep = {}
    rep['iso'] = iso
    rep['atlas'] = dict(name=atlas['name'], psm=psm, w=w, h=h,
                        clut=atlas['clut'], px_size=atlas['px_size'], px_off=atlas['px_off'])
    px = atflow = D.container_blob(atlas)
    rep['px_container_bytes'] = len(px)
    segs = tcslib.atlas_container_segments(px, w // 2 if psm == 0x14 else w)
    rep['gif_segments'] = [dict(first_row=r, off=o, bytes=l) for (r, o, l) in segs]

    # ---- FONT.RES faces ----
    fl = []
    for (nm, fld, recs) in faces:
        fl.append(dict(name=nm, nrec=len(recs), fld=list(fld)))
    rep['faces'] = fl
    rep['face_count'] = len(faces)

    # ---- grid geometry ----
    rep['grid'] = dict(NCOL=tcslib.NCOL, CW=tcslib.CW, CH=tcslib.CH, Y0=tcslib.GRID_Y0,
                       skip_row=tcslib.GRID_SKIP_ROW, skip_rows=tcslib.GRID_SKIP_ROWS,
                       stride=tcslib.PAIR_STRIDE)
    rows = usable_grid_rows(h)
    rep['grid_rows_in_current_atlas'] = dict(count=len(rows),
                                             first=rows[0] if rows else None,
                                             last=rows[-1] if rows else None)
    # rows lost to the 3-row hole
    hole = [r for r in range(256)
            if tcslib.GRID_SKIP_ROW <= r < tcslib.GRID_SKIP_ROW + tcslib.GRID_SKIP_ROWS]
    rep['hole_rows'] = hole

    slots = tcslib.pair_capacity()
    rep['current_slot_capacity'] = slots
    last_row = (slots - 1) // tcslib.NCOL
    last_col = (slots - 1) % tcslib.NCOL
    rep['last_slot'] = dict(row=last_row, col=last_col, x=tcslib.CW * last_col,
                            y=grid_yrow(last_row))
    # cells in the last used row that the slot formula cannot reach
    tail = tcslib.NCOL - 1 - last_col
    rep['unreachable_tail_cells_row%d' % last_row] = tail

    # ---- candidate levers ----
    lev = {}

    def cells_for_h(new_h):
        rws = usable_grid_rows(new_h)
        # rows fully above the ASCII band are free unless already used by slots
        used_rows = set()
        for s in range(slots):
            used_rows.add(s // tcslib.NCOL)
        free = [(r, y) for (r, y) in rws if r not in used_rows]
        # subtract the ASCII band rows (occupied by FT record rects) - reported raw here
        return rws, free

    for new_h in (512, 768, 1024, 1280, 2048):
        rws, free = cells_for_h(new_h)
        lev['h=%d' % new_h] = dict(
            total_grid_rows=len(rws),
            max_row=rws[-1][0] if rws else None,
            max_y=rws[-1][1] if rws else None,
            grid_cells=len(rws) * tcslib.NCOL,
            rows_above_last_used=len([r for (r, y) in rws if r > last_row]),
            raw_new_cells=len([1 for (r, y) in rws if r > last_row]) * tcslib.NCOL,
        )
    rep['levers_atlas_height'] = lev

    # ---- text-icon / single-byte band census ----
    cs = tcslib.Charset()
    singles = sorted(set(cs.enc_single.values())) if hasattr(cs, 'enc_single') else []
    rep['charset'] = dict(
        n_single=len(getattr(cs, 'enc_single', {}) or {}),
        n_pair=len(getattr(cs, 'enc_pair', {}) or {}),
    )

    rep['lead_gate'] = dict(lo=tcslib.LEAD_LO, hi=tcslib.LEAD_HI,
                            n_leads=tcslib.LEAD_HI - tcslib.LEAD_LO,
                            trail_lo=tcslib.PAIR_TRAIL_LO, trail_hi=tcslib.PAIR_TRAIL_HI,
                            stride=tcslib.PAIR_STRIDE)

    txt = json.dumps(rep, indent=1, ensure_ascii=False)
    print(txt)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(txt)


main()
