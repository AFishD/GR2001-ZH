# -*- coding: utf-8 -*-
"""G6: correlate every TLB-miss burst in the live emulog with the nearest known frame."""
import os, re, json

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
LOG = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\logs\emulog.txt")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")

lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
re_frame = re.compile(r"frame=(\d+)")
re_miss = re.compile(r"^\[\s*([\d.]+)\]\s+TLB Miss, pc=0x([0-9a-fA-F]+) addr=0x([0-9a-fA-F]+) \[(\w+)\]")
re_f10 = re.compile(r"F10 pressed \(frame (\d+)\)")

last_frame = None
events = []
cur = None
for i, ln in enumerate(lines):
    m = re_frame.search(ln)
    if m:
        last_frame = int(m.group(1))
    m = re_miss.match(ln)
    if m:
        t, pc, ad, kind = float(m.group(1)), int(m.group(2), 16), int(m.group(3), 16), m.group(4)
        if cur is None or t - cur["t_end"] > 0.05:
            cur = dict(t0=t, t_end=t, frame=last_frame, line=i + 1, items=[])
            events.append(cur)
        cur["t_end"] = t
        cur["items"].append((pc, ad, kind))
    m = re_f10.search(ln)
    if m:
        events.append(dict(f10=int(m.group(1)), t0=float(re.match(r"^\[\s*([\d.]+)\]", ln).group(1)), line=i + 1))

L = []
L.append("TLB-miss bursts in the live emulog, grouped (>50 ms gap = new burst) and tied to the")
L.append("nearest preceding HookWatch 'frame=' value.  The hook logs a frame number every 2000 hits,")
L.append("so frame is accurate to about +-5 frames.")
L.append("")
for ev in events:
    if "f10" in ev:
        L.append("--- [%.4f s, emulog line %d]  F10 pressed -> dump at frame %d" % (ev["t0"], ev["line"], ev["f10"]))
        L.append("")
        continue
    uniq = sorted(set(a for (_p, a, _k) in ev["items"]))
    pcs = sorted(set(p for (p, _a, _k) in ev["items"]))
    L.append("--- [%.4f..%.4f s, emulog lines %d..] frame ~%s   %d TLB misses"
             % (ev["t0"], ev["t_end"], ev["line"], ev["frame"], len(ev["items"])))
    L.append("    distinct PCs : %s" % " ".join("%08X" % p for p in pcs))
    L.append("    distinct addr: %s" % " ".join("%08X" % a for a in uniq[:24]))
    if len(uniq) > 24:
        L.append("                   ... (%d more distinct addrs)" % (len(uniq) - 24))
    L.append("    first 20 raw :")
    for (pc, ad, kind) in ev["items"][:20]:
        L.append("       pc=%08X addr=%08X %s" % (pc, ad, kind))
    L.append("")

# classify every distinct 'garbage chunk pointer' seen
gp = {}
for ev in events:
    if "f10" in ev:
        continue
    for (pc, ad, kind) in ev["items"]:
        if ad >= 0x02000000:
            gp.setdefault(ad, []).append((ev["frame"], ev["t0"], pc, kind))
L.append("")
L.append("distinct >32 MB (unmapped) addresses touched, with the frames they appear in:")
for ad in sorted(gp):
    fr = sorted(set(str(x[0]) for x in gp[ad]))
    L.append("  0x%08X  frames=%s  (first pc=%08X %s)" % (ad, ",".join(fr), gp[ad][0][2], gp[ad][0][3]))

open(os.path.join(OUT, "g6_tlb_bursts.txt"), "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L))
