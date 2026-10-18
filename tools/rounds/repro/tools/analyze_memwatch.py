#!/usr/bin/env python3
"""GR_REPRO: diff two -grmemwatch captures (record = [u32 frame][u32 addr][u32 size][data]).

Typical use: control (no input) vs triggered (L1 pressed) over the same address range,
so the bytes the game wrote *because of the trigger* fall out directly.
"""
import argparse
import struct
import sys


def load(path):
    with open(path, "rb") as f:
        blob = f.read()
    recs = {}
    order = []
    off = 0
    while off + 12 <= len(blob):
        frame, addr, size = struct.unpack_from("<III", blob, off)
        data = blob[off + 12:off + 12 + size]
        if len(data) != size:
            break
        recs[frame] = (addr, size, data)
        order.append(frame)
        off += 12 + size
    return recs, order, len(blob)


def first_changes(recs, order):
    """offset -> (frame, old, new) for the first frame each byte changed from the first sample."""
    if not order:
        return {}
    base = recs[order[0]][2]
    seen = {}
    for fr in order:
        data = recs[fr][2]
        for i in range(min(len(base), len(data))):
            if i in seen:
                continue
            if data[i] != base[i]:
                seen[i] = (fr, base[i], data[i])
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control")
    ap.add_argument("triggered")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-offsets", type=int, default=64)
    a = ap.parse_args()

    cout = []
    def w(s=""):
        cout.append(s)
        print(s)

    crecs, corder, cbytes = load(a.control)
    trecs, torder, tbytes = load(a.triggered)
    w(f"control  : {a.control}")
    w(f"           {cbytes} bytes, {len(corder)} records, frames {min(corder)}..{max(corder)}")
    w(f"triggered: {a.triggered}")
    w(f"           {tbytes} bytes, {len(torder)} records, frames {min(torder)}..{max(torder)}")

    addr, size, _ = trecs[torder[0]]
    w(f"region   : addr={addr:#010x} size={size} (record={size + 12} bytes)")
    w()

    common = sorted(set(corder) & set(torder))
    w(f"common frames: {len(common)} (first={common[0]}, last={common[-1]})")
    w()

    # 1) whole-run divergence: offsets whose value ever differs between the two runs
    diff_offsets = {}
    for fr in common:
        cd = crecs[fr][2]
        td = trecs[fr][2]
        for i in range(min(len(cd), len(td))):
            if cd[i] != td[i]:
                diff_offsets.setdefault(i, []).append((fr, cd[i], td[i]))
    w(f"[A] offsets differing between control and triggered: {len(diff_offsets)}")
    for i in sorted(diff_offsets)[: a.max_offsets]:
        ev = diff_offsets[i]
        first = ev[0]
        w(f"    va={addr + i:#010x} off={i:#06x}  first frame={first[0]}  "
          f"control={first[1]:#04x} triggered={first[2]:#04x}  events={len(ev)}")
    if len(diff_offsets) > a.max_offsets:
        w(f"    ... {len(diff_offsets) - a.max_offsets} more")
    w()

    # 2) per-run first change from the first sample
    for tag, recs, order in (("control", crecs, corder), ("triggered", trecs, torder)):
        ch = first_changes(recs, order)
        frames = sorted({v[0] for v in ch.values()})
        w(f"[B] {tag}: {len(ch)} offsets changed from the frame-{order[0]} snapshot; "
          f"change frames={frames[:24]}{' ...' if len(frames) > 24 else ''}")
        per_frame = {}
        for i, (fr, old, new) in ch.items():
            per_frame.setdefault(fr, []).append(i)
        for fr in sorted(per_frame)[:16]:
            offs = sorted(per_frame[fr])
            w(f"      frame {fr}: {len(offs)} byte(s): " +
              ", ".join(f"{addr + o:#010x}:{ch[o][1]:02x}->{ch[o][2]:02x}" for o in offs[:12]) +
              (" ..." if len(offs) > 12 else ""))
        w()

    # 3) the narrow allocator window called out by the task
    for name, base in (("malloc_state@0x0055B7A0", 0x7A0),):
        lo = max(0, base - 32)
        hi = min(size, base + 224)
        w(f"[C] window {name}: bytes {addr + lo:#010x}..{addr + hi:#010x}")
        for fr in common:
            cd = crecs[fr][2]
            td = trecs[fr][2]
            if cd[lo:hi] != td[lo:hi]:
                d = [i for i in range(lo, hi) if cd[i] != td[i]]
                w(f"      frame {fr}: {len(d)} differing byte(s): " +
                  ", ".join(f"+{i - base:#06x} c={cd[i]:02x} t={td[i]:02x}" for i in d[:16]))
        w()

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(cout) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
