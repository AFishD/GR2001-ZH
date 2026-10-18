# -*- coding: utf-8 -*-
r"""probe4.py — 核心实验:
  A) ZH92 与 EN_ORIG 的容器是否逐字节相同 (⇒ 英文原盘可当「假阳性对照组」)
  B) 文本串长度阈值 vs 覆盖率 (选默认 --min-run)
"""
import hashlib
import json
import os
import re
import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T  # noqa: E402

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
EN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
c = json.load(open(CS, encoding='utf-8'))
BTN = (0xB1, 0xB5, 0xE7, 0xF1)
alphabet = bytes(sorted(set(range(0x20, 0x7F)) |
                        {int(v) for v in c['codes'].values()} |
                        {v[0] for v in c['pair_of'].values()} |
                        {v[1] for v in c['pair_of'].values()} | set(BTN)))
RX4 = re.compile(b'[' + re.escape(alphabet) + b']{4,}')
THRESH = (4, 8, 12, 16, 24, 32, 48, 64)


def enum_containers(iso, lba, tag):
    base = lba * T.SEC
    noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
    names = [x.decode('latin-1') for x in bytes(iso.mm[base + noff:base + nend]).split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', iso.mm, base + T.TAB_OFF + T.TAB_STEP * i)
        stored, real, off = r[6], r[7], r[8]
        if not stored or not off:
            continue
        out.append(dict(img=tag, idx=i, name=nm, stored=stored, real=real, off=off))
    return out


def load_all(path):
    iso = T.Iso(path)
    cs = []
    for lba, tag in ((T.GR_LBA, 'GR.IMG'), (T.MENU_LBA, 'MENU.IMG')):
        cs += enum_containers(iso, lba, tag)
    return iso, cs


t0 = time.time()
izh, czh = load_all(ZH)
ien, cen = load_all(EN)
print('枚举: ZH92 %d 个容器, EN_ORIG %d 个容器 (%.1fs)' % (len(czh), len(cen), time.time() - t0))

# ── A) 逐字节比对 ──
key = lambda x: (x['img'], x['idx'])
mzh = {key(x): x for x in czh}
men = {key(x): x for x in cen}
same = diff = only_zh = only_en = 0
diffs = []
t1 = time.time()
for k, a in mzh.items():
    b = men.get(k)
    if b is None:
        only_zh += 1
        continue
    if a['name'] != b['name'] or a['stored'] != b['stored']:
        diff += 1
        diffs.append((k, a['name'], a['stored'], b['stored'], 'size/name'))
        continue
    base_a = (T.GR_LBA if a['img'] == 'GR.IMG' else T.MENU_LBA) * T.SEC
    base_b = (T.GR_LBA if b['img'] == 'GR.IMG' else T.MENU_LBA) * T.SEC
    ha = hashlib.sha1(bytes(izh.mm[base_a + a['off']:base_a + a['off'] + a['stored']])).digest()
    hb = hashlib.sha1(bytes(ien.mm[base_b + b['off']:base_b + b['off'] + b['stored']])).digest()
    if ha == hb:
        same += 1
    else:
        diff += 1
        diffs.append((k, a['name'], a['stored'], b['stored'], 'bytes'))
only_en = len(set(men) - set(mzh))
print('\n[A] 容器逐字节比对 (%.1fs): 相同 %d, 不同 %d, 仅ZH92有 %d, 仅EN有 %d'
      % (time.time() - t1, same, diff, only_zh, only_en))
print('    不同的容器:')
for k, nm, sa, sb, why in sorted(diffs)[:80]:
    print('      %-9s #%-5d %-24s zh=%-9d en=%-9d %s' % (k[0], k[1], nm, sa, sb, why))

# ── B) 文本串阈值 vs 覆盖率 ──
cover = {t: 0 for t in THRESH}
tot_blob = 0
t2 = time.time()
for x in czh:
    base = (T.GR_LBA if x['img'] == 'GR.IMG' else T.MENU_LBA) * T.SEC
    raw = bytes(izh.mm[base + x['off']:base + x['off'] + x['stored']])
    if x['stored'] != x['real']:
        blob = b''.join(s[0] for s in T.lzo_subs(raw))
    else:
        blob = raw
    tot_blob += len(blob)
    for m in RX4.finditer(blob):
        L = m.end() - m.start()
        for t in THRESH:
            if L >= t:
                cover[t] += L
print('\n[B] 扫描 %d B (%.1f MB), 耗时 %.1fs' % (tot_blob, tot_blob / 1048576, time.time() - t2))
for t in THRESH:
    print('    run>=%-3d 覆盖 %12d B (%.3f%%)' % (t, cover[t], 100.0 * cover[t] / tot_blob))
izh.close()
ien.close()
