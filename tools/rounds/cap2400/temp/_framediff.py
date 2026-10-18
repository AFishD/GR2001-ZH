import glob, os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = r"work\builds\GR_CAP2400\temp\dump_probe644"
B = r"work\builds\GR_CAP2400\temp\dump_base"
fa = {os.path.basename(p): p for p in glob.glob(os.path.join(A, "snap_*.png"))}
fb = {os.path.basename(p): p for p in glob.glob(os.path.join(B, "snap_*.png"))}
rows = []
for n in sorted(set(fa) & set(fb)):
    ia = np.asarray(Image.open(fa[n]).convert("RGB")).astype(np.int16)
    ib = np.asarray(Image.open(fb[n]).convert("RGB")).astype(np.int16)
    if ia.shape != ib.shape:
        rows.append((n, -1, -1)); continue
    d = (np.abs(ia - ib).sum(axis=2) > 0)
    rows.append((n, int(d.sum()), ia.shape[0]*ia.shape[1]))
diff = [r for r in rows if r[1] != 0]
print("不同张数 %d / %d" % (len(diff), len(rows)))
for n, dn, tot in diff:
    print("   %s 不同像素 %6d / %d (%.2f%%)" % (n, dn, tot, 100.0*dn/max(1,tot)))
