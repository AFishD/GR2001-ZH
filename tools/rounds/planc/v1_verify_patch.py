# -*- coding: utf-8 -*-
r"""v1_verify_patch.py — 独立复核 patch_zh93_planc 的产物:
  ① ELF 4 处 gate = 0xB1
  ② 图集: 17 个新字形格逐像素一致; 其余像素与基盘一致 (只多这 1622 px)
  ③ charset: 17 字 encode/decode 往返; 旧 1300 字里"没被本次改动"的字映射不变
  ④ 打印落点表
只读。
"""
import hashlib
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH93_planc', 'GR_ZH93_planc.iso')
OLD_CS = os.path.join(HERE, 'charset_before_planc.json')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
W, H, CW, CH = 1024, 512, 16, 16
GATES = [(0x416EE8, 0xB1), (0x417160, 0xB1), (0x41751C, 0xB1), (0x5656A4, 0xB1)]
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


fnt = ImageFont.truetype(FZ, 16)


def render(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def atlas_of(path):
    iso = tcslib.Iso(path)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    fa = [r for r in tcslib.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    nb = np.frombuffer(pak[fa[6]:fa[6] + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    return A, pak


print('== ① ELF gate ==')
d = open(NEW, 'rb').read(ELF_LBA * 2048 + SEC_OFF + 0x600000)
ok = True
for va, want in GATES:
    o = ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)
    w = struct.unpack_from('<I', d, o)[0]
    good = (w & 0xFFFF) == want
    ok &= good
    print('  0x%06X = %08X  imm=0x%02X %s' % (va, w, w & 0xFFFF, '✓' if good else '✗'))
print('  4 处全部 = 0x%02X : %s' % (GATES[0][1], '✓' if ok else '✗'))
print('  sha256(新盘) = %s' % hashlib.sha256(open(NEW, 'rb').read()).hexdigest())

print()
print('== ② 图集 ==')
Ab, _ = atlas_of(BASE)
An, _ = atlas_of(NEW)
INb, INn = (Ab == 0), (An == 0)
diff = INb != INn
print('  与基盘不同的像素 = %d' % int(diff.sum()))
js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
meta = js['_font_ext_planc_zh93']
bad = 0
print('  字  码位   槽位   引擎格       写入后逐像素')
for ch, txt in meta['placed'].items():
    parts = txt.split()
    code = parts[0]
    slot = int([p for p in parts if p.startswith('slot=')][0][5:])
    r, c = slot // 62, slot % 62
    x, y = 16 * ((c + PHI[r]) % 64), yrow(r)
    if '新写字形' in txt:
        g = render(ch)
        good = (INn[y:y + CH, x:x + CW] == g).all()
    else:
        good = int(INn[y:y + CH, x:x + CW].sum()) > 20 and not diff[y:y + CH, x:x + CW].any()
    bad += (not good)
    print('  %s  %s  %4d  (%4d,%3d)   %s' % (ch, code, slot, x, y, '✓' if good else '✗'))

print()
print('== ③ charset ==')
old = json.load(open(OLD_CS, encoding='utf-8'))
new = json.load(open(tcslib.CHARSET, encoding='utf-8'))
print('  codes  %d → %d ; pair_of %d → %d'
      % (len(old['codes']), len(new['codes']), len(old['pair_of']), len(new['pair_of'])))
assert tcslib.PAIR_LEAD_HI == 0xB1 and tcslib.LEAD_HI == 0xB1, (
    tcslib.PAIR_LEAD_HI, tcslib.LEAD_HI)
print('  tcslib LEAD_HI/PAIR_LEAD_HI = 0x%02X ✓' % tcslib.PAIR_LEAD_HI)
cs = tcslib.Charset()
moved = {'的', '你', '荐'}
kept_pair = [ch for ch in old['pair_of'] if ch not in moved and ch not in meta['placed']]
chg = [ch for ch in kept_pair if tuple(old['pair_of'][ch]) != tuple(new['pair_of'].get(ch, ()))]
print('  未改动的旧对偶字 %d 个，映射被改的 %d 个 %s' % (len(kept_pair), len(chg), chg[:5]))
kept_single = [ch for ch, c in old['codes'].items() if ch not in moved]
chg2 = [ch for ch in kept_single if old['codes'][ch] != new['codes'].get(ch)]
print('  未改动的旧单字节字 %d 个，映射被改的 %d 个 %s' % (len(kept_single), len(chg2), chg2[:5]))
rt = 0
for ch in list(new['pair_of']) + list(new['codes']):
    b = cs.encode_strict(ch)
    back, _ = cs.decode(b)
    if back != ch:
        print('  ✗ 往返失败 %s → %s' % (ch, b.hex()))
    rt += (back == ch)
print('  encode_strict/decode 往返: %d/%d ✓' % (rt, len(new['pair_of']) + len(new['codes'])))
# 旧盘全量往返 (抽样: 用户译文里用到的字符)
import csv
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
txt = set()
for fn in sorted(os.listdir(TXT)):
    if fn.endswith('.csv'):
        with open(os.path.join(TXT, fn), encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                txt.update(r.get('text_edited') or '')
print('  用户译文用字 %d 个：其中 charset 无映射的 %s'
      % (len(txt), ''.join(sorted(c for c in txt
                                 if c not in new['codes'] and c not in new['pair_of']
                                 and ord(c) >= 0x80))))
print()
print('  落点总览: %d 字 →' % len(meta['placed']))
for ch, t in meta['placed'].items():
    print('     %s %s' % (ch, t))
