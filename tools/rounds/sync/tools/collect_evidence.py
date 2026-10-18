#!/usr/bin/env python3
"""collect_evidence.py -- preserve a compact evidence file per GR_SYNC run, then the big
emulog.txt / per-frame RAM dumps can be deleted (disk discipline).

Writes <run>/evidence.txt with:
  * anomaly census + first anomaly lines of emulog.txt
  * the '"GR: setting override"' / MTVU / renderer readback lines
  * watch.txt (verbatim) and the pcsample PC trajectory
  * sha256 of the per-frame EE RAM dumps (so the raw 33 MB files can be dropped)
"""
import hashlib, os, re, sys

RUNS_ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\runs"

def main(runs):
    for run in runs:
        d = os.path.join(RUNS_ROOT, run)
        log = os.path.join(d, "emulog.txt")
        out = []
        if os.path.exists(log):
            trap = tlb = unrec = 0
            firsts, readback, pc_first = [], [], {}
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "Trap exception" in line:
                        trap += 1
                        m = re.search(r"Trap exception at (0x[0-9a-fA-F]+)", line)
                        if m: pc_first[m.group(1)] = pc_first.get(m.group(1), 0) + 1
                        if len(firsts) < 3: firsts.append(line.rstrip())
                    elif "TLB Miss" in line:
                        tlb += 1
                        if len(firsts) < 6: firsts.append(line.rstrip())
                    elif "Unrecognized op" in line:
                        unrec += 1
                        if len(firsts) < 8: firsts.append(line.rstrip())
                    elif any(k in line for k in ("MTVU speedhack", "Bios Found", "BIOS Found",
                                                 "D3D12: Creating", "D3D11: Creating", "ps_5_1",
                                                 "Enabling MTVU", "Disabling MTVU")):
                        readback.append(line.rstrip())
            out.append(f"# {run}\n")
            out.append(f"traps={trap} tlb_miss={tlb} unrecognized_op={unrec}")
            out.append(f"trap PCs: {pc_first}")
            out.append("\n## first anomaly lines")
            out += firsts
            out.append("\n## boot readback (renderer/MTVU/BIOS)")
            out += sorted(set(readback))
        for name in ("watch.txt", "pcsample.txt"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                out.append(f"\n## {name}")
                out.append(open(p, encoding="utf-8", errors="replace").read().rstrip())
        dumps = sorted(f for f in os.listdir(d) if re.match(r"win_f\d+_eeram\.bin$", f))
        if dumps:
            out.append("\n## per-frame EE RAM dump hashes (raw files deleted)")
            for f in dumps:
                h = hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest()
                out.append(f"{f}  {os.path.getsize(os.path.join(d,f))}  {h}")
        with open(os.path.join(d, "evidence.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
        print(f"{run}: evidence.txt written ({len(out)} lines)")

if __name__ == "__main__":
    main(sys.argv[1:])
