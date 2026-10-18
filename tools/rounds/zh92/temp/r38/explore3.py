# -*- coding: utf-8 -*-
r"""explore3.py — 计时: 全量 LZO 解压 / regex 文本串扫描 / numpy 双字节直方图"""
import os
import re
import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T  # noqa: E402
import numpy as np  # noqa: E402
import json  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
c = json.load(open(CS, encoding='utf-8'))
alphabet = bytes(sorted(set(range(0x20, 0x7F)) |
                        {int(v) for v in c['codes'].values()} |
                        {v[0] for v in c['pair_of'].values()} |
                        {v[1] for v in c['pair_of'].values()}))
RX = re.compile(b'[' + re.escape(alphabet) + b']{8,}')
print('alphabet n=%d' % len(alphabet))

iso = T.Iso(ISO)
mm = iso.mm
base = T.GR_LBA * T.SEC
noff = struct.unpack_from('<I', mm, base + 0x10)[0]
nend = struct.unpack_from('<I', mm, base + 4)[0]
names = [x.decode('latin-1') for x in bytes(mm[base + noff:base + nend]).split(b'\x00') if x]

# 只取前 300 个非 PSS/SS/TM 的条目做计时样本
picks = []
for i, nm in enumerate(names):
    e = os.path.splitext(nm)[1].upper()
    if e in ('.PSS', '.SS', '.TM', '.MPG', '.M2V', '.SB'):
        continue
    r = struct.unpack_from('<12I', mm, base + T.TAB_OFF + T.TAB_STEP * i)
    stored, real, off = r[6], r[7], r[8]
    picks.append((nm, stored, real, off))
    if len(picks) >= 400:
        break
tot_stored = sum(p[1] for p in picks)
tot_real = sum(p[2] for p in picks)
print('样本 %d 条, stored=%.1f MB real=%.1f MB' % (len(picks), tot_stored / 1048576,
                                                   tot_real / 1048576))

t0 = time.time()
ndec = 0
nrun_bytes = 0
nrun_hits = 0
hist = np.zeros(65536, dtype=np.int64)
hist1 = np.zeros(256, dtype=np.int64)
for nm, stored, real, off in picks:
    raw = iso.read(base + off, stored)
    if stored != real:
        blob = b''.join(s[0] for s in T.lzo_subs(raw))
        ndec += len(blob)
    else:
        blob = raw
    # L2: regex 文本串
    for m in RX.finditer(blob):
        nrun_bytes += m.end() - m.start()
        nrun_hits += 1
    # L3: numpy 直方图
    a = np.frombuffer(blob, dtype=np.uint8)
    if len(a) > 1:
        hist += np.bincount(a.astype(np.uint16) * 256 + np.roll(a, -1).astype(np.uint16),
                            minlength=65536)[:65536]
        hist1 += np.bincount(a, minlength=256)
t1 = time.time()
print('解压得 %d B; 耗时 %.1fs' % (ndec, t1 - t0))
print('文本串(L2): %d 段, 合计 %d B (占 %.2f%%)' % (nrun_hits, nrun_bytes,
                                                  100.0 * nrun_bytes / max(1, tot_real)))
print('numpy 直方图: 非零 bigram %d / 65536; 非零单字节 %d / 256'
      % (int((hist > 0).sum()), int((hist1 > 0).sum())))
iso.close()
