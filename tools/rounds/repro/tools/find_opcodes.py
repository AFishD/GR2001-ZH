#!/usr/bin/env python3
"""GR_REPRO: find the exact EE RAM location of the 'EE: Unrecognized op' words
printed by PCSX2 at the crash, so the corrupted fetch region is identified.

Each word is searched little-endian (PS2 is LE) in the per-frame EE RAM dumps.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

WORDS = [
    "EFD7080E", "740090D5", "EFD36F0A", "C19095A1", "4EE51400",
    "F390A100", "009000FD", "CA36D721", "000090D5", "47009051", "E0809870",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    buf = []
    def w(s=""):
        buf.append(s)
        print(s)

    for d in a.dirs:
        files = sorted(glob.glob(os.path.join(d, "win_f*_eeram.bin")))
        # also allow the one-shot needle dumps
        files += sorted(glob.glob(os.path.join(d, "*_eeram.bin")))
        w(f"=== {d}: {len(files)} dump(s)")
        for p in files:
            data = np.fromfile(p, dtype=np.uint8)
            for hexw in WORDS:
                pat = bytes.fromhex(hexw)[::-1]          # little-endian on disk
                needle = np.frombuffer(pat, dtype=np.uint8)
                if data.size < 4:
                    continue
                # rolling search using a 4-byte view
                win = np.lib.stride_tricks.sliding_window_view(data, 4)
                hits = np.flatnonzero((win == needle).all(axis=1))
                if hits.size:
                    w(f"  {os.path.basename(p)}  {hexw}: {hits.size} hit(s) at " +
                      ", ".join(f"{int(h):#010x}" for h in hits[:8]))
        w()

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(buf) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
