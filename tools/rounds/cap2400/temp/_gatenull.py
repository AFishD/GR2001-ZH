import glob, hashlib, os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = r"work\builds\GR_CAP2400\temp\dump_probe644"
B = r"work\builds\GR_CAP2400\temp\dump_nogate644"
fa = {os.path.basename(p): p for p in glob.glob(os.path.join(A, "snap_*.png"))}
fb = {os.path.basename(p): p for p in glob.glob(os.path.join(B, "snap_*.png"))}
same = 0; diff = []
for n in sorted(set(fa) & set(fb)):
    if hashlib.sha256(open(fa[n],"rb").read()).hexdigest() == hashlib.sha256(open(fb[n],"rb").read()).hexdigest():
        same += 1
    else:
        ia = np.asarray(Image.open(fa[n]).convert("RGB")).astype(np.int16)
        ib = np.asarray(Image.open(fb[n]).convert("RGB")).astype(np.int16)
        diff.append((n, int((np.abs(ia-ib).sum(axis=2) > 0).sum())))
print("probe644 (GATE BA) vs nogate644 (GATE B4): 同名 %d 张, 逐字节相同 %d, 不同 %d" % (len(fa), same, len(diff)))
for n, d in diff[:12]: print("   %s 不同像素 %d" % (n, d))
