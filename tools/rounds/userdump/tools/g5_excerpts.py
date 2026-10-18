# -*- coding: utf-8 -*-
"""G5: key ring excerpts + emulog snapshot + cross-session bin126 corroboration."""
import os, struct, json, hashlib, shutil, io

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
DUMPS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\hookdumps")
LOGS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\logs")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")
EV = os.path.join(ROOT, r"work\builds\GR_USERDUMP\evidence")
BB = 0x0055B7A8
BE = BB + 128 * 8
B126 = (0x0055BB98, 0x0055BB9C)
os.makedirs(EV, exist_ok=True)

# ---------- 1) emulog snapshot (the file is held open by the running pcsx2-qt) ----------
src = os.path.join(LOGS, "emulog.txt")
snap = os.path.join(EV, "emulog_snapshot_2026-10-18.txt")
buf = bytearray()
with open(src, "rb") as f:            # python opens with FILE_SHARE_READ|WRITE on Windows
    while True:
        c = f.read(1 << 20)
        if not c:
            break
        buf += c
open(snap, "wb").write(buf)
h = hashlib.sha256(bytes(buf)).hexdigest()
print("emulog snapshot: %d bytes  sha256=%s" % (len(buf), h))
open(os.path.join(EV, "emulog_snapshot_sha256.txt"), "w").write(
    "source=%s\nbytes=%d\nsha256=%s\nnote=live emulog is held open by the running pcsx2-qt (pid 45040); "
    "this is a point-in-time read-only snapshot taken by the analysis session\n" % (src, len(buf), h))

# ---------- 2) ring excerpts ----------
def parse_ring(path):
    b = open(path, "rb").read()
    for i in range(len(b) // 24):
        o = i * 24
        fr, pc, ad = struct.unpack_from("<III", b, o)
        val = struct.unpack_from("<Q", b, o + 12)[0]
        size, pad, dr, src2 = b[o + 20], b[o + 21], b[o + 22], b[o + 23]
        yield (i, fr, pc, ad, size, chr(dr), src2, val)

L = []
A = L.append
for tag, dn in (("OLD f19701", "hook_19701_hotkey_f10"), ("NEW f23444", "hook_23444_hotkey_f10")):
    recs = list(parse_ring(os.path.join(DUMPS, dn, "ring.bin")))
    A("=" * 108)
    A("%s  ring frames %d..%d  records=%d" % (tag, recs[0][1], recs[-1][1], len(recs)))
    A("=" * 108)
    # 2a) any write overlapping the bucket-126 slots?
    hits = [r for r in recs if r[3] < B126[1] + 4 and r[3] + max(1, r[4] // 8) > B126[0]]
    A("  writes overlapping bin-126 slots 0x%08X/0x%08X : %d" % (B126[0], B126[1], len(hits)))
    for r in hits[:20]:
        A("    idx=%d f=%d pc=%08X addr=%08X size=%d %s val=0x%016X" % (r[0], r[1], r[2], r[3], r[4], r[5], r[7]))
    # 2b) the insert pair for the LARGE bins (hook PC 00102014 / 00102018) - chronological sample
    pair = [r for r in recs if r[2] in (0x00102014, 0x00102018)]
    A("")
    A("  large-bin insert pair (hook PC 00102014 / 00102018) = %d records; first 14 and last 6:" % len(pair))
    sel = pair[:14] + pair[-6:]
    for r in sel:
        b = (r[3] - BB) // 8
        fld = "fd" if (r[3] - BB) % 8 == 0 else "bk"
        A("    idx=%d f=%d pc=%08X addr=%08X size=%d %s val=0x%08X   (bin %d %s)"
          % (r[0], r[1], r[2], r[3], r[4], r[5], r[7] & 0xFFFFFFFF, b, fld))
    # 2c) all writes to the top bins 118..127 (any PC)
    hi = [r for r in recs if BB <= r[3] < BE and (r[3] - BB) // 8 >= 118]
    A("")
    A("  all writes to bins 118..127 (any PC): %d" % len(hi))
    for r in hi:
        b = (r[3] - BB) // 8
        fld = "fd" if (r[3] - BB) % 8 == 0 else "bk"
        A("    f=%d pc=%08X addr=%08X size=%d %s val=0x%08X  -> bin %d %s"
          % (r[1], r[2], r[3], r[4], r[5], r[7] & 0xFFFFFFFF, b, fld))
    # 2d) last 3 records before the ring's oldest (i.e. what we cannot see)
    A("")
    A("  oldest record in ring: idx=%d frame=%d pc=%08X addr=%08X" % (recs[0][0], recs[0][1], recs[0][2], recs[0][3]))
    A("  newest record in ring: idx=%d frame=%d pc=%08X addr=%08X" % (recs[-1][0], recs[-1][1], recs[-1][2], recs[-1][3]))
    A("")
open(os.path.join(OUT, "g5_ring_excerpts.txt"), "w", encoding="utf-8").write("\n".join(L))
print("g5_ring_excerpts.txt written, lines=%d" % len(L))

# ---------- 3) cross-session corroboration from the previous round's audits ----------
AUD = os.path.join(ROOT, r"work\builds\GR_HEAP\evidence\audits")
A2 = []
A2.append("cross-session bin-126 values recorded by the PREVIOUS round (docs\\REPORT_HEAP_EXHAUSTION.md / GR_HEAP\\evidence\\audits)")
A2.append("(all from disc CRC 7A761FCA or other builds - NOT the same session as the user's two dumps)")
A2.append("")
for fn in sorted(os.listdir(AUD)):
    p = os.path.join(AUD, fn)
    try:
        j = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        A2.append("  %-34s <unreadable %r>" % (fn, e))
        continue
    # find anything that mentions 55BB98 / 55bb98 / bin126
    s = json.dumps(j)
    keys = [k for k in j.keys()]
    interesting = {}
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for n, v in enumerate(o):
                walk(v, path + "[%d]" % n)
        else:
            if "55BB98" in path.upper() or "55BB9C" in path.upper() or "BIN126" in path.upper() or "126" in path:
                interesting[path] = o
    walk(j)
    A2.append("  %-34s keys=%s" % (fn, ",".join(keys[:8])))
    for k, v in list(interesting.items())[:6]:
        A2.append("        %s = %r" % (k, v))
open(os.path.join(OUT, "g5_prior_audits.txt"), "w", encoding="utf-8").write("\n".join(A2))
print("g5_prior_audits.txt written")
