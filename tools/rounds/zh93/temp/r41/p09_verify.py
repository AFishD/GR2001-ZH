# -*- coding: utf-8 -*-
r"""p09_verify.py — round41 验收自查 (读 CSV, 不改任何东西)。

V1 新 CSV 的 cell_legacy_x/y == **改版前** dump 的 cell_x/cell_y (逐行, 1526 行)
V2 新 CSV 的 cell_x/cell_y (对偶) == tcslib.atlas_cell_xy_engine(slot) (1319 行)
V3 新 CSV 的 cell_x/cell_y (对偶) != legacy 的 slot 数 (应当 = 全部 1319)
V4 has_glyph 变化 (旧 21 缺 → 新 ?) 逐字列出
V5 note 里能看到判定依据 + 引擎格信息
V6 单字节/ASCII 的 cell_x/cell_y 与 legacy 的关系 (相位校正)
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

OLD = os.path.join(HERE, 'baseline', 'GR_ZH93_font_charset.csv')
NEW = os.path.join(HERE, 'run1', 'GR_ZH93_font_charset.csv')


def load(p):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    old, new = load(OLD), load(NEW)
    print('旧 CSV %d 行 / 新 CSV %d 行' % (len(old), len(new)))
    print('旧列: %s' % ','.join(old[0].keys()))
    print('新列: %s' % ','.join(new[0].keys()))
    rc = 0

    # ---- V1: legacy 两列 == 旧 cell 两列 ----
    key = lambda r: (r['kind'], r['bytes_hex'], r['unicode'])
    o = {key(r): r for r in old}
    n = {key(r): r for r in new}
    assert set(o) == set(n), '两版 CSV 的行集合不同: 只在旧 %d / 只在新 %d' % (
        len(set(o) - set(n)), len(set(n) - set(o)))
    bad = [(k, o[k]['cell_x'], o[k]['cell_y'], n[k]['cell_legacy_x'], n[k]['cell_legacy_y'])
           for k in o if (o[k]['cell_x'], o[k]['cell_y'])
           != (n[k]['cell_legacy_x'], n[k]['cell_legacy_y'])]
    print('\n[V1] cell_legacy_* == 旧 dump 的 cell_* : %s (不一致 %d 行)'
          % ('OK ✓' if not bad else '**失败**', len(bad)))
    for b in bad[:10]:
        print('     %s 旧=(%s,%s) 新legacy=(%s,%s)' % b)
    rc |= bool(bad)

    # ---- V2/V3: 对偶行的引擎格 ----
    rows = [r for r in new if r['kind'] == 'pair']
    mis, same = [], 0
    for r in rows:
        s = int(r['slot'])
        x, y = tcslib.atlas_cell_xy_engine(s)
        if (int(r['cell_x']), int(r['cell_y'])) != (x, y):
            mis.append((s, r['char'], r['cell_x'], r['cell_y'], x, y))
        if (int(r['cell_x']), int(r['cell_y'])) == (int(r['cell_legacy_x']), int(r['cell_legacy_y'])):
            same += 1
    print('[V2] 对偶行 %d 条: cell_x/cell_y == atlas_cell_xy_engine : %s (不一致 %d)'
          % (len(rows), 'OK ✓' if not mis else '**失败**', len(mis)))
    print('[V3] 其中 cell_x/cell_y 与 cell_legacy_* **相同**的: %d 条 (应 = 0: 两者恒不同)'
          % same)
    rc |= bool(mis) or bool(same)

    # ---- V4: has_glyph 变化 ----
    diffs = [(k, o[k]['has_glyph'], n[k]['has_glyph'], o[k]['note'], n[k]['note'])
             for k in o if o[k]['has_glyph'] != n[k]['has_glyph']]
    print('\n[V4] has_glyph 变化的字: %d 个' % len(diffs))
    for k, a, b, on, nn in diffs:
        print('     %s %s: %s → %s' % (k[0], k[2], a, b))
        print('        旧 note: %s' % on[:150])
        print('        新 note: %s' % nn[:150])
    n_old_missing = sum(1 for r in old if r['has_glyph'] == '0')
    n_new_missing = sum(1 for r in new if r['has_glyph'] == '0')
    print('     缺字形总数: 旧 %d → 新 %d' % (n_old_missing, n_new_missing))
    n_old_pair_ok = sum(1 for r in old if r['kind'] == 'pair' and r['has_glyph'] == '1')
    n_new_pair_ok = sum(1 for r in new if r['kind'] == 'pair' and r['has_glyph'] == '1')
    print('     对偶字有字形: 旧 %d → 新 %d (对偶总数 %d)'
          % (n_old_pair_ok, n_new_pair_ok, len(rows)))

    # ---- V5: note 里有依据 ----
    kinds = {}
    for r in new:
        kinds.setdefault(r['kind'], []).append(r)
    print('\n[V5] 每类各取 2 行看 note / glyph_basis:')
    for k in ('pair', 'single', 'ascii', 'icon'):
        for r in kinds.get(k, [])[:2]:
            print('     [%s] %s %s cell=(%s,%s) legacy=(%s,%s) has_glyph=%s basis=%s'
                  % (k, r['char'], r['bytes_hex'], r['cell_x'], r['cell_y'],
                     r['cell_legacy_x'], r['cell_legacy_y'], r['has_glyph'], r['glyph_basis']))
            print('          note: %s' % r['note'][:160])

    # ---- V6: 单字节/ASCII 的相位校正统计 ----
    n_shift = sum(1 for r in new if r['kind'] in ('single', 'ascii')
                  and r['cell_x'] and r['cell_legacy_x']
                  and (r['cell_x'] != r['cell_legacy_x'] or r['cell_y'] != r['cell_legacy_y']))
    print('\n[V6] 单字节/ASCII 里 cell != legacy (做过行相位校正) 的: %d / %d'
          % (n_shift, len(kinds.get('single', [])) + len(kinds.get('ascii', []))))
    print('     (ASCII 全在 EN 带、不在网格行 ⇒ 不做校正 ⇒ 应当只有单字节码被校正)')

    print('\n验收自查结论: %s' % ('全部通过 ✓' if not rc else '**有失败项** ✗'))
    return 0 if not rc else 1


if __name__ == '__main__':
    sys.exit(main())
