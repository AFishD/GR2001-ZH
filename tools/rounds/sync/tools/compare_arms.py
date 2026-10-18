#!/usr/bin/env python3
"""compare_arms.py -- compare the two GR_SYNC arms of the savestate repro.

For each arm: anomaly census of emulog.txt, pcsample PC trajectory, watch.txt hits.
Across arms: byte-level diff of the per-frame EE RAM dumps (win_f0000004X_eeram.bin)
written by -grdumpwin 40 46. Identical dumps => the settings did not change the
emulated machine's state at all up to the crash.

usage: python compare_arms.py <runA> <runB> [...]
"""
import os, re, sys, hashlib

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\runs"

def census(run):
    log = os.path.join(ROOT, run, "emulog.txt")
    n = {"trap": 0, "tlb": 0, "unrec": 0}
    first = []
    first_trap_t = first_unrec_t = None
    trap_pc = {}
    with open(log, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Trap exception" in line:
                n["trap"] += 1
                m = re.search(r"Trap exception at (0x[0-9a-fA-F]+)", line)
                if m: trap_pc[m.group(1)] = trap_pc.get(m.group(1), 0) + 1
                if first_trap_t is None:
                    tm = re.match(r"\[\s*([\d.]+)\]", line)
                    first_trap_t = tm.group(1) if tm else "?"
                    first.append(line.rstrip()[:120])
            elif "TLB Miss" in line:
                n["tlb"] += 1
                if len(first) < 6: first.append(line.rstrip()[:120])
            elif "Unrecognized op" in line:
                n["unrec"] += 1
                if first_unrec_t is None:
                    tm = re.match(r"\[\s*([\d.]+)\]", line)
                    first_unrec_t = tm.group(1) if tm else "?"
                    if len(first) < 4: first.append(line.rstrip()[:120])
    return n, first_trap_t, first_unrec_t, trap_pc, first

def pcsample(run):
    p = os.path.join(ROOT, run, "pcsample.txt")
    out = []
    if os.path.exists(p):
        for line in open(p):
            parts = line.split()
            if len(parts) == 2: out.append((int(parts[0]), parts[1]))
    return out

def watch(run):
    p = os.path.join(ROOT, run, "watch.txt")
    hits = []
    if os.path.exists(p):
        for line in open(p, encoding="utf-8", errors="replace"):
            if line.startswith("hit "): hits.append(line.rstrip())
    return hits

def dump_hashes(run):
    d = os.path.join(ROOT, run)
    out = {}
    for f in sorted(os.listdir(d)):
        m = re.match(r"win_f(\d+)_eeram\.bin$", f)
        if m:
            data = open(os.path.join(d, f), "rb").read()
            out[int(m.group(1))] = (hashlib.sha256(data).digest(), data)
    return out

def diff(data_a, data_b):
    """bytes differing, and the first/last differing offset"""
    if len(data_a) != len(data_b): return None
    n = 0; first = last = -1
    for i in range(len(data_a)):
        if data_a[i] != data_b[i]:
            n += 1
            if first < 0: first = i
            last = i
    return n, first, last

def main(runs):
    info = {}
    for r in runs:
        n, ft, fu, tpc, first = census(r)
        info[r] = dict(n=n, first_trap=ft, first_unrec=fu, trap_pc=tpc, first=first,
                       pc=pcsample(r), watch=watch(r), dumps=dump_hashes(r))
        print(f"== {r}")
        print(f"   traps={n['trap']}  tlb_miss={n['tlb']}  unrecognized_op={n['unrec']}")
        print(f"   first 'Trap exception' @ {ft}s ; first 'Unrecognized op' @ {fu}s")
        print(f"   trap PCs: {tpc}")
        print(f"   pcsample: {info[r]['pc']}")
        print(f"   watch hits: {len(info[r]['watch'])}")
        late = [w for w in info[r]['watch'] if int(re.search(r"frame=(\d+)", w).group(1)) >= 38]
        print(f"   watch hits at frame>=38: {len(late)}")
        for w in late[:20]:
            print(f"      {w}")
        for w in info[r]['watch'][:8]:
            print(f"      [early] {w}")
        print(f"   frame dumps: {sorted(info[r]['dumps'].keys())}")
    if len(runs) >= 2:
        a, b = runs[0], runs[1]
        print(f"\n== cross-arm EE RAM comparison ({a} vs {b})")
        da, db = info[a]['dumps'], info[b]['dumps']
        for fr in sorted(set(da) | set(db)):
            if fr not in da or fr not in db:
                print(f"   frame {fr}: only in {'A' if fr in da else 'B'}")
                continue
            same = da[fr][0] == db[fr][0]
            if same:
                print(f"   frame {fr}: IDENTICAL (sha256 {da[fr][0].hex()[:16]})")
            else:
                d = diff(da[fr][1], db[fr][1])
                print(f"   frame {fr}: DIFFERS bytes={d[0]} first=0x{d[1]:X} last=0x{d[2]:X}")
        # per-arm intra-frame diffs (what the failing frames change inside one arm)
        for r in runs:
            dd = info[r]['dumps']; fr = sorted(dd)
            print(f"\n== {r}: consecutive-frame EE RAM diffs (frames {fr[0]}..{fr[-1]})")
            for i in range(1, len(fr)):
                d = diff(dd[fr[i-1]][1], dd[fr[i]][1])
                print(f"   {fr[i-1]} -> {fr[i]}: bytes={d[0]} first=0x{d[1]:X} last=0x{d[2]:X}")

if __name__ == "__main__":
    main(sys.argv[1:])
