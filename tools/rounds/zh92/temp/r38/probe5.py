# -*- coding: utf-8 -*-
r"""probe5.py — 随机数据里 T2 判据的噪声本底 (定标用)"""
import os
import random
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
import font_usage as F  # noqa: E402

idx = F.CharsetIndex()
pairs = [p for p in idx.pair_of if F.LEGAL_LEAD_LO <= p[0] < F.LEGAL_LEAD_HI]
print('合法对偶字 %d 个' % len(pairs))
random.seed(20261005)
for mb in (1, 8):
    rnd = bytes(random.randrange(256) for _ in range(mb << 20))
    for t in (8, 16, 24, 32, 48):
        hit = set()
        cov = 0
        for m in idx.run_re(4).finditer(rnd):
            L = m.end() - m.start()
            if L < t:
                continue
            cov += L
            for ch in idx.decode_chars(m.group(0)):
                hit.add(ch)
        hp = [c for c in hit if c in idx.enc_pair]
        print('  %d MB 随机: run>=%-3d 覆盖 %9d B (%.3f%%)  命中字 %4d  其中对偶 %4d'
              % (mb, t, cov, 100.0 * cov / len(rnd), len(hit), len(hp)))
