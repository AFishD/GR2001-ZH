import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
dirs = [("base   (h512/62列/GATE B4)", r"work\builds\GR_CAP2400\temp\dump_base"),
        ("nogate (h644/64列/GATE B4)", r"work\builds\GR_CAP2400\temp\dump_nogate644"),
        ("probe  (h644/64列/GATE BA)", r"work\builds\GR_CAP2400\temp\dump_probe644"),
        ("probe660(h660/62列/GATE BA)", r"work\builds\GR_CAP2400\temp\dump_probe660")]
name = "snap_f00002700.png"
box = (110, 108, 215, 255)
tiles = []
for tag, d in dirs:
    im = Image.open(os.path.join(d, name)).convert("RGB").crop(box)
    s = 4
    im = im.resize((im.size[0]*s, im.size[1]*s), Image.NEAREST)
    lab = Image.new("RGB", (im.size[0], 26), (255,255,255))
    ImageDraw.Draw(lab).text((3, 7), tag, fill=(0,0,0))
    t = Image.new("RGB", (im.size[0], im.size[1]+26), (255,255,255))
    t.paste(lab, (0,0)); t.paste(im, (0,26))
    tiles.append(t)
W = sum(t.size[0] for t in tiles) + 8*(len(tiles)-1)
H = max(t.size[1] for t in tiles)
canvas = Image.new("RGB", (W, H), (255,255,255))
x = 0
for t in tiles:
    canvas.paste(t, (x, 0)); x += t.size[0] + 8
p = r"work\builds\GR_CAP2400\temp\cmp_3way_f2700.png"
canvas.save(p)
print("saved", p, canvas.size)
# 顺便: 逐对差异
arrs = [np.asarray(Image.open(os.path.join(d, name)).convert("RGB")).astype(np.int16) for _t, d in dirs]
for i in range(1, len(dirs)):
    d = (np.abs(arrs[i]-arrs[0]).sum(axis=2) > 0)
    print("%-30s vs base: 不同像素 %d" % (dirs[i][0], int(d.sum())))
d2 = (np.abs(arrs[2]-arrs[1]).sum(axis=2) > 0)
print("probe vs nogate (只看抬闸门的影响): 不同像素 %d" % int(d2.sum()))
ys, xs = np.nonzero(d2)
if len(ys): print("   bbox x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
