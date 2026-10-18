import collections, glob, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = r"work\builds\GR_CAP2400\temp\dump_probe644"
hs = collections.OrderedDict()
for p in sorted(glob.glob(os.path.join(d, "snap_*.png"))):
    h = hashlib.sha256(open(p,"rb").read()).hexdigest()
    hs.setdefault(h, []).append(os.path.basename(p))
print("scenes:", len(hs))
for i, (h, fs) in enumerate(hs.items()):
    print("%2d %s x%-3d %s" % (i, h[:10], len(fs), fs[0]))
