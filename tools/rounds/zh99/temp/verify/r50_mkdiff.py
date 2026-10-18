# -*- coding: utf-8 -*-
r"""r50_mkdiff.py — 对每个 nav 把 GR_ZH98(前) 与 GR_ZH99(后) 的同名快照逐像素对比, 并定量定性。"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                          # noqa: E402
from PIL import Image                                       # noqa: E402

NAVS = sys.argv[1:] or ['menu', 'weapon', 'doc']
out = {}
for nav in NAVS:
    a = os.path.join(HERE, 'dump_r50_%s_zh98' % nav)
    b = os.path.join(HERE, 'dump_r50_%s_zh99' % nav)
    if not (os.path.isdir(a) and os.path.isdir(b)):
        print('[skip] %s: 抓帧目录不全' % nav)
        continue
    rep = os.path.join(HERE, 'ab_diff_%s.json' % nav)
    log = os.path.join(HERE, 'ab_diff_%s.log' % nav)
    print('=' * 72)
    print('[diff] nav=%s' % nav)
    with io.open(log, 'w', encoding='utf-8', newline='\n') as f:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'r50_diff.py'), a, b,
                            '--out', rep, '--tag', 'r50_%s' % nav],
                           stdout=f, stderr=subprocess.STDOUT)
    txt = io.open(log, encoding='utf-8', errors='replace').read()
    print(txt[-800:])
    d = json.load(io.open(rep, encoding='utf-8')) if os.path.isfile(rep) else {}
    # 定量: 差异帧的 maxΔ
    hard = []
    for rec in d.get('detail', []):
        if 'n' not in rec:
            continue
        ia = np.asarray(Image.open(os.path.join(a, rec['frame'])).convert('RGB')).astype(int)
        ib = np.asarray(Image.open(os.path.join(b, rec['frame'])).convert('RGB')).astype(int)
        dm = np.abs(ia - ib).max(axis=2)
        hard.append((rec['frame'], int(rec['n']), int(dm.max()), int((dm > 2).sum())))
    out[nav] = dict(rc=r.returncode, frames_common=d.get('frames_common'),
                    frames_same=d.get('frames_same'), frames_diff=d.get('frames_diff'),
                    hard=hard[:40])
io.open(os.path.join(HERE, 'ab_diff_all.json'), 'w', encoding='utf-8',
        newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print('=' * 72)
print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
