# -*- coding: utf-8 -*-
r"""s9_impact.py — 影响面量化: 网格行 19..24 的槽位/字符有多少, 用户译文里出现多少次。

口径: drift(row) = (PHI[row] - flat_x_shift(yrow)/16) mod 64 = 字形实际所在的引擎列 - 它应该在的列。
      引擎画 slot(row,col) 时读引擎格 (16*col, yrow) ⇒ 显示的是 col' = (col - drift) mod 64 那一列的字。
只读 (charset JSON + 用户表 + tcslib)。
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                     # noqa: E402

USER_TEXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text')
LOG = []


def log(s):
    print(s)
    LOG.append(s)


def main():
    cs = tcslib.Charset()
    by_slot = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        by_slot[tcslib.pair_slot(b1, b2)] = ch

    # 用户译文里各字出现次数
    freq = {}
    for fn in sorted(glob.glob(os.path.join(USER_TEXT, '*.csv'))):
        with io.open(fn, encoding='utf-8-sig', newline='') as f:
            import csv as _csv
            for row in _csv.DictReader(f):
                t = row.get('text_edited') or ''
                for ch in t:
                    freq[ch] = freq.get(ch, 0) + 1
    log('[txt] 用户表 %s: 共 %d 个不同字符, %d 字次'
        % (os.path.relpath(USER_TEXT, REPO),
           len(freq), sum(freq.values())))

    log('')
    log('[drift] 每网格行: (写入侧 flat 格 - 引擎采样格) 的差(格), 0 = 同一个物理位置')
    log('   row   yrow   PHI  flat错位(格)  drift  该行已用槽  其中错位')
    rows = {}
    drift = {}
    for row in range(25):
        y = tcslib.GRID_Y0 + tcslib.CH * (row + (tcslib.GRID_SKIP_ROWS if row >= tcslib.GRID_SKIP_ROW else 0))
        ph = tcslib.atlas_row_phase(row)
        sh = tcslib.atlas_flat_x_shift(y) // tcslib.CW
        d = (ph - sh) % 64
        drift[row] = d
        used = [s for s in by_slot if s // tcslib.NCOL == row]
        rows[row] = used
        log('  %4d %6d %5d %12d %6d %11d %9d'
            % (row, y, ph, sh, d, len(used),
               len(used) if d else 0))

    bad_slots = [s for row in range(25) for s in rows[row] if drift[row]]
    bad_chars = [by_slot[s] for s in bad_slots]
    bad_freq = sum(freq.get(c, 0) for c in bad_chars)
    log('')
    log('[影响] 字形不在引擎采样格上的**已用槽位**: %d 个 (占已用 %d 个的 %.1f%%)'
        % (len(bad_slots), len(by_slot), 100.0 * len(bad_slots) / max(1, len(by_slot))))
    log('[影响] 涉及字符 %d 个; 在用户译文里合计出现 %d 次'
        % (len(bad_chars), bad_freq))
    logs = {}
    for row in range(19, 25):
        d = drift[row]
        if not d:
            continue
        pred_pairs = []
        for s in rows[row][:6]:
            col = s % tcslib.NCOL
            col2 = (col - d) % 64
            s2 = row * tcslib.NCOL + col2 if col2 < tcslib.NCOL else None
            pred_pairs.append('%s(col%02d)→显示 %s'
                              % (by_slot[s], col,
                                 by_slot.get(s2, '（第 %d 列：本行不采样/回绕副本）' % col2)
                                 if s2 is not None else '（第 %d 列：本行不采样）' % col2))
        logs[row] = pred_pairs
        log('[影响] 行 %d (偏 %d 格): %s' % (row, d, '; '.join(pred_pairs)))
    top = sorted(((freq.get(c, 0), c) for c in bad_chars), reverse=True)[:20]
    log('[影响] 受影响字符里在译文里出现最多的 20 个: %s'
        % ' '.join('%s×%d' % (c, n) for n, c in top if n))
    with io.open(os.path.join(HERE, 's9_impact.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(drift=drift, bad_slot_count=len(bad_slots), bad_char_count=len(bad_chars),
                       bad_char_freq=bad_freq, rows=dict((str(k), len(v)) for k, v in rows.items()),
                       bad_chars=''.join(sorted(bad_chars)), examples=logs,
                       top_used=[[c, n] for n, c in top]),
                  f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(HERE, 's9_impact.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
