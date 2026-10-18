#!/usr/bin/env python3
"""GR_REPRO: byte diff of two EE RAM dumps (same run, consecutive frames) -> the writes
performed during that frame. Immune to the input-reaction bias of control-vs-triggered."""
import argparse
import sys

import numpy as np


def runs(mask, max_runs):
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    sp = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[sp + 1]]
    en = np.r_[idx[sp] + 1, idx[-1] + 1]
    order = np.argsort(-(en - st))
    return [(int(st[i]), int(en[i])) for i in order[:max_runs]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--max-runs", type=int, default=20)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    b = np.fromfile(a.before, dtype=np.uint8)
    f = np.fromfile(a.after, dtype=np.uint8)
    n = min(b.size, f.size)
    b, f = b[:n], f[:n]
    d = b != f
    buf = []
    def w(s=""):
        buf.append(s)
        print(s)

    w(f"before: {a.before}")
    w(f"after : {a.after}")
    w(f"changed bytes: {int(d.sum())}")
    w()
    for (s, e) in runs(d, a.max_runs):
        w(f"{s:#010x}..{e:#010x} len={e - s}")
        w(f"   before: {b[s:e][:64].tobytes().hex()}")
        w(f"   after : {f[s:e][:64].tobytes().hex()}")
    w()
    # low EE RAM (exception vectors) explicitly
    lo, hi = 0, 0x300
    dl = np.flatnonzero(d[lo:hi])
    w(f"changes inside 0x00000000..0x{hi:x} (exception vectors / BIOS low memory): {dl.size} byte(s)")
    for i in dl[:96]:
        w(f"   {i:#06x}: {b[i]:02x} -> {f[i]:02x}")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(buf) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
