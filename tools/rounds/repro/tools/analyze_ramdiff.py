#!/usr/bin/env python3
"""GR_REPRO: byte-level diff of per-frame EE RAM dumps (win_f%08u_eeram.bin).

Compares two runs of the same savestate (control vs triggered) frame by frame and
prints the differing contiguous runs, so the fields the trigger corrupted fall out.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

FRAME_RE = re.compile(r"win_f(\d+)_eeram\.bin$")


def load_frames(d):
    out = {}
    for p in glob.glob(os.path.join(d, "win_f*_eeram.bin")):
        m = FRAME_RE.search(p)
        if m:
            out[int(m.group(1))] = p
    return out


def runs(mask, max_runs):
    """contiguous True-runs of a boolean array -> [(start, end_exclusive)]"""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    splits = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[splits + 1]]
    ends = np.r_[idx[splits] + 1, idx[-1] + 1]
    order = np.argsort(-(ends - starts))
    return [(int(starts[i]), int(ends[i])) for i in order[:max_runs]]


def hexs(b):
    return b.tobytes().hex()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control_dir")
    ap.add_argument("triggered_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-runs", type=int, default=12)
    ap.add_argument("--pre-crash-only", action="store_true")
    a = ap.parse_args()

    cf = load_frames(a.control_dir)
    tf = load_frames(a.triggered_dir)
    common = sorted(set(cf) & set(tf))
    buf = []
    def w(s=""):
        buf.append(s)
        print(s)

    w(f"control  : {a.control_dir}  frames={sorted(cf)}")
    w(f"triggered: {a.triggered_dir}  frames={sorted(tf)}")
    w(f"common frames: {common}")
    w()

    first_diff_frame = None
    for fr in common:
        c = np.fromfile(cf[fr], dtype=np.uint8)
        t = np.fromfile(tf[fr], dtype=np.uint8)
        n = min(c.size, t.size)
        c, t = c[:n], t[:n]
        d = c != t
        nd = int(d.sum())
        w(f"--- frame {fr}: {nd} differing byte(s) of {n} ({100.0 * nd / n:.4f}%)")
        if nd:
            if first_diff_frame is None:
                first_diff_frame = fr
            rs = runs(d, a.max_runs)
            for (s, e) in rs:
                cs = c[s:e]
                ts = t[s:e]
                w(f"      {s:#010x}..{e:#010x} len={e - s}")
                w(f"        control  : {hexs(cs[:48])}{' ...' if e - s > 48 else ''}")
                w(f"        triggered: {hexs(ts[:48])}{' ...' if e - s > 48 else ''}")
        w()

    if first_diff_frame is not None:
        w(f"FIRST differing frame: {first_diff_frame}")
        # word-level summary at the first differing frame
        c = np.fromfile(cf[first_diff_frame], dtype=np.uint8)
        t = np.fromfile(tf[first_diff_frame], dtype=np.uint8)
        n = min(c.size, t.size) & ~3
        cw = c[:n].view("<u4")
        tw = t[:n].view("<u4")
        sel = np.flatnonzero(cw != tw)
        w(f"word-level differences at frame {first_diff_frame}: {sel.size}")
        for i in sel[:80]:
            w(f"      {i * 4:#010x}: control={cw[i]:#010x} triggered={tw[i]:#010x}")
        if sel.size > 80:
            w(f"      ... {sel.size - 80} more")
    else:
        w("no differing frame found (runs are byte-identical in the dumped window)")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(buf) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
