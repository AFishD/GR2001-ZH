"""r73_band_census.py -- per-atlas-row ink census of the shipping font atlas.

Purpose: answer (D) "is the 12px band a second font or the same texture?" and give the
report hard numbers for which atlas rows are occupied / free.

Read-only.
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
    gray = D.atlas_gray(atlas, 'engine')
    print(f"atlas {w}x{h} psm=0x{atlas['psm']:X}  ink total = {sum(1 for b in gray[:w*h] if b == 0)}")

    print("\nrow : ink_texels  (16-px band)   grid_row  yrow")
    for r in range(h // 16):
        y = r * 16
        band = gray[y * w:(y + 16) * w]
        ink = sum(1 for b in band if b == 0)
        gr = [k for k in range(80)
              if tcslib.GRID_Y0 + tcslib.CH * (k + (tcslib.GRID_SKIP_ROWS if k >= tcslib.GRID_SKIP_ROW else 0)) == y]
        print(f"  row{r:3d} y={y:4d}..{y+15:4d} : {ink:7d}   grid_row={gr if gr else '-'}")

    # 12px band specifically
    print("\n--- 12px band v=480..495 ---")
    b = gray[480 * w:496 * w]
    print("  ink texels =", sum(1 for x in b if x == 0))
    print("  is a grid row? ",
          any(tcslib.GRID_Y0 + tcslib.CH * (k + (tcslib.GRID_SKIP_ROWS if k >= tcslib.GRID_SKIP_ROW else 0)) == 480
              for k in range(80)))


main()
