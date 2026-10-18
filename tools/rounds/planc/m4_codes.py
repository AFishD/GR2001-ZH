# -*- coding: utf-8 -*-
r"""m4_codes.py — 码位普查: 单字节占用 / 空闲码 / 死 pair / 盘上裸码扫描。

只读 (不写任何文件)。
"""
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

CS = tcslib.CHARSET
js = json.load(open(CS, encoding='utf-8'))
codes = {ch: int(v) for ch, v in js['codes'].items()}
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}

print('== 单字节码 (111) ==')
inv = {}
for ch, c in codes.items():
    inv.setdefault(c, []).append(ch)
for c in sorted(inv):
    print('  0x%02X %s' % (c, ''.join(inv[c])), end='')
    if (c + 1) % 8 == 0:
        print()
print()

leads_used = sorted({v[0] for v in pair_of.values()})
print()
print('== pair lead 分布 ==')
for L in leads_used:
    n = sum(1 for v in pair_of.values() if v[0] == L)
    slot0 = (L - 0xA1) * 94
    print('  lead 0x%02X : %3d 条, slot %d..%d, 行 %d..%d'
          % (L, n, slot0, slot0 + 93, slot0 // 62, (slot0 + 93) // 62))

dead = {ch: v for ch, v in pair_of.items() if v[0] >= 0xAE}
dead_with_single = [ch for ch in dead if ch in codes]
dead_only_pair = [ch for ch in dead if ch not in codes]
print()
print('== 死 pair (lead>=0xAE, 现役盘引擎读不出) ==')
print('  合计 %d 条; 其中**同时有单字节码**的 %d 个: %s'
      % (len(dead), len(dead_with_single), ''.join(dead_with_single)))
print('  只有死 pair、没有单字节码的 %d 个: %s'
      % (len(dead_only_pair), ''.join(dead_only_pair)))

print()
print('== 空闲单字节码 (0x80..0xFF 中既非单字节汉字、也非 pair lead 的) ==')
free = []
for c in range(0x80, 0x100):
    if c in inv:
        continue
    if 0xA1 <= c <= 0xAD:
        continue
    if any(v[0] == c for v in pair_of.values()):
        continue
    free.append(c)
print('  %d 个: %s' % (len(free), ' '.join('0x%02X' % c for c in free)))

print()
print('== 0xAE..0xB3 逐个查 ==')
for c in range(0xAE, 0xB4):
    s = inv.get(c)
    p = sum(1 for v in pair_of.values() if v[0] == c)
    print('  0x%02X : 单字节=%s  有 %d 条 pair 记录' % (c, (''.join(s) if s else '空'), p))

# ---------------- 盘上裸码扫描 ----------------
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))


def scan_blob(buf, gate_hi, label):
    """gate_hi = 新 lead 上界 (exclusive)。返回裸码统计 (0xAE..gate_hi-1 里未被配对吃掉的字节)"""
    cnt = {}
    i = 0
    n = len(buf)
    while i < n:
        v = buf[i]
        if 0xA1 <= v < gate_hi and i + 1 < n and 0xA1 <= buf[i + 1] <= 0xFE:
            i += 2
            continue
        if 0xAE <= v <= 0xB3:
            cnt[v] = cnt.get(v, 0) + 1
        i += 1
    return cnt, label


for (lba, idx, nm) in ((tcslib.MENU_LBA, 25, 'MENU#25 EN_STRINGS.RES'),
                       (tcslib.MENU_LBA, tcslib.XML_IDX, 'MENU#283 SF.XML'),
                       (tcslib.GR_LBA, 902, 'GR#902 EN_STRINGS.RES')):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = tcslib.lzo_subs(raw)
    blob = b''.join(s[0] for s in subs)
    print()
    print('== %s: name=%s stored=%d real=%d 展开=%d 子流=%d =='
          % (nm, e['name'], e['stored'], e.get('real'), len(blob), len(subs)))
    for gate in (0xAE, 0xAF, 0xB4):
        cnt, _ = scan_blob(blob, gate, nm)
        print('   gate=0x%02X (lead 0xA1..0x%02X): 裸码 %s'
              % (gate, gate - 1, {hex(k): v for k, v in sorted(cnt.items())} or '{}'))
iso.close()

print()
print('== 用户 CSV 表里的 0xAE..0xB3 单字节字出现次数 ==')
for fn in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text'))):
    if not fn.endswith('.csv'):
        continue
    p = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text', fn)
    txt = open(p, encoding='utf-8-sig', newline='').read()
    hits = []
    for c in range(0xAE, 0xB4):
        for ch in inv.get(c, []):
            if ch in txt:
                hits.append('0x%02X(%s x%d)' % (c, ch, txt.count(ch)))
    if hits:
        print('  %-40s %s' % (fn, ' '.join(hits)))
