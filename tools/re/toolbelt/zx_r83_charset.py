# -*- coding: utf-8 -*-
r"""zx_r83_charset.py — round83：把 charset 收敛到「1504 现役 + 232 新槽 (1504..1735)」状态

  python tools/re/toolbelt/zx_r83_charset.py --dry-run
  python tools/re/toolbelt/zx_r83_charset.py --apply

规则:
  · pair_of 的 slot 0..1503 = **原样保留**（现役 1504 个字，码位/格位一字不动）
  · slot 1504..1507 = △/键/练/用（gate 0xB1→0xB4 后 0xB1..0xB3 变成 lead，必须迁移）
  · slot 1508..1735 = r82/rich_missing_chars.csv 里的前 228 个缺字（按 CSV 顺序）
  · **删除** slot 1736..1871 的登记（本盘没有这些格）
  · codes 保持 107 条不变（0xB6..0xFF + 0x80..0xA0）
"""
import argparse
import csv
import io
import json
import os
import shutil
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib      # noqa: E402

R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
R83 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
CH = tcslib.CHARSET
SLOT_LO, SLOT_HI = 1504, 1735
MIGRATE = ['△', '键', '练', '用']


def build():
    cs = json.load(io.open(CH, encoding='utf-8'))
    base = json.load(io.open(os.path.join(R82, 'charset_before_r82.json'), encoding='utf-8'))
    cur = dict(cs['pair_of'])
    old = dict(base['pair_of'])
    # 校验 slot 0..1503 与 base 一致
    bad = [(ch, cur[ch], old.get(ch)) for ch in old if tcslib.pair_slot(*cur[ch]) <= 1503
           and old.get(ch) != cur[ch]]
    inv = {}
    for ch, p in cur.items():
        s = tcslib.pair_slot(*p)
        if s <= 1503:
            inv.setdefault(s, []).append(ch)
    n_base = sum(1 for s in inv if s <= 1503)
    print('[charset] 现役 slot<=1503: 唯一槽 %d ; 与 base 不同的字 %d %s'
          % (n_base, len(bad), bad[:6]))
    miss = []
    with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            miss.append(r['char'])
    print('[charset] 缺字清单 %d' % len(miss))
    new = {}
    for s, ch in enumerate(MIGRATE):
        new[ch] = [tcslib.pair_from_slot(SLOT_LO + s)[0], tcslib.pair_from_slot(SLOT_LO + s)[1]]
    n_new = 0
    for ch in miss:
        s = SLOT_LO + len(MIGRATE) + n_new
        if s > SLOT_HI:
            break
        if ch in new:
            continue
        new[ch] = list(tcslib.pair_from_slot(s))
        n_new += 1
    print('[charset] 迁移 %d + 新字 %d = %d 条 ⇒ 新 pair_of 总 %d'
          % (len(MIGRATE), n_new, len(new), len(inv) + len(new)))
    out = dict(cs)
    pairs = {}
    for s in sorted(inv):
        pairs[inv[s][0]] = cur[inv[s][0]]
    pairs.update(new)
    out['pair_of'] = pairs
    out['_expand_r83'] = {
        'note': 'round83: gate 0xB1→0xB4; 新字只用 slot 1504..1735 (row 24 尾 16..61 / row 25..27 全行); '
                'h 保持 512, 容器/PAK/MENU 尺寸全不变; 原 slot 1736..1871 的登记已删除',
        'gate_new': 0xB4, 'slot_lo': SLOT_LO, 'slot_hi': SLOT_HI,
        'n_migrated': len(MIGRATE), 'n_new': n_new,
        'dropped_slots': [1736, 1871],
        'migrated': {c: list(new[c]) for c in MIGRATE},
    }
    return cs, out, new, n_new, miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    cs, out, new, n_new, miss = build()
    if not a.apply:
        print('[dry-run] 未写 charset')
        return 0
    bk = os.path.join(R83, 'charset_before_r83.json')
    if not os.path.exists(bk):
        shutil.copy2(CH, bk)
        print('[backup] %s' % bk)
    with io.open(CH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('[charset] 已写 %s (pair_of %d → %d)' % (CH, len(cs['pair_of']), len(out['pair_of'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
