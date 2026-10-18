import os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = r"work\builds\GR_CAP2400\temp\dump_probe644"
B = r"work\builds\GR_CAP2400\temp\dump_base"
OUT = r"work\builds\GR_CAP2400\temp"
for name in ("snap_f00002700.png", "snap_f00001500.png", "snap_f00002280.png", "snap_f00002490.png"):
    ia = np.asarray(Image.open(os.path.join(A, name)).convert("RGB")).astype(np.int16)
    ib = np.asarray(Image.open(os.path.join(B, name)).convert("RGB")).astype(np.int16)
    d = (np.abs(ia - ib).sum(axis=2) > 0)
    ys, xs = np.nonzero(d)
    if len(ys) == 0:
        print(name, "identical"); continue
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    print("%s diff px=%d bbox x %d..%d y %d..%d" % (name, len(ys), x0, x1, y0, y1))
    pad = 12
    xa, xb = max(0, x0-pad), min(ia.shape[1], x1+1+pad)
    ya, yb = max(0, y0-pad), min(ia.shape[0], y1+1+pad)
    ca = Image.open(os.path.join(A, name)).convert("RGB").crop((xa, ya, xb, yb))
    cb = Image.open(os.path.join(B, name)).convert("RGB").crop((xa, ya, xb, yb))
    s = 3
    ca = ca.resize((ca.size[0]*s, ca.size[1]*s), Image.NEAREST)
    cb = cb.resize((cb.size[0]*s, cb.size[1]*s), Image.NEAREST)
    canvas = Image.new("RGB", (ca.size[0], ca.size[1]*2 + 6), (255, 0, 0))
    canvas.paste(cb, (0, 0)); canvas.paste(ca, (0, ca.size[1]+6))
    p = os.path.join(OUT, "cmp_%s.png" % name.replace("snap_f", "f").replace(".png", ""))
    canvas.save(p)
    print("   saved", p, "(上=基底盘, 下=探针盘)")
