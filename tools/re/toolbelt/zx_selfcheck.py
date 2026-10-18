# -*- coding: utf-8 -*-
r"""zx_selfcheck.py — 只读: 用 tcslib 自己的口径复核 charset + 全量文本覆盖 (P3 前置)

  [1] tcslib.selfcheck_charset 全条 (含 round82 改过的 placeholder 段)
  [2] 丰富版三张表的每个字: 能否编码 + 盘上是否有字形 (GlyphCache.check_text)
  [3] 新 368 个码位的编码/解码往返 + 引擎格坐标 + 该格在盘上的墨量
用法: python zx_selfcheck.py [--iso <iso>] [--text <dir>]
"""
import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402
import csv                                                           # noqa: E402

REPO = zx_lib.REPO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH121',
                                                  'GR_ZH121.iso'))
    ap.add_argument('--text', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                   'text_backup_before_r71'))
    a = ap.parse_args()
    cs = tcslib.Charset()
    ok, lines = tcslib.selfcheck_charset(cs)
    n_bad = sum(1 for ln in lines if ln.startswith('[!!]'))
    print('[1] selfcheck_charset: %d 条, 其中 [!!] %d 条 ⇒ %s'
          % (len(lines), n_bad, 'PASS' if ok else 'FAIL'))
    for ln in lines:
        if ln.startswith('[!!]'):
            print('    ' + ln)
    print('    pair_of %d ; codes %d ; pair_capacity %d'
          % (len(cs.enc_pair), len(cs.enc_single), tcslib.pair_capacity()))

    print('\n[2] 全量文本覆盖 (丰富版口径) + 盘上字形')
    iso = tcslib.Iso(a.iso) if os.path.exists(a.iso) else None
    gc = tcslib.GlyphCache(cs, iso)
    rows = 0
    problems = []
    for fp in sorted(glob.glob(os.path.join(a.text, '*_text_*.csv'))):
        if '_view_' in os.path.basename(fp):
            continue
        with io.open(fp, encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                t = r.get('text_edited') or ''
                if not t:
                    continue
                rows += 1
                for p in gc.check_text(t):
                    problems.append((os.path.basename(fp), r['id'], p))
    print('    已改行 %d ; 问题 %d 条' % (rows, len(problems)))
    kinds = {}
    for (_f, _i, p) in problems:
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    print('    问题分类: %s' % kinds)
    for (f, i, p) in problems[:10]:
        print('      %s %s %s' % (f, i, p.get('reason')))
    if iso:
        iso.close()

    print('\n[3] 新码位抽查 (368 个新 pair)')
    if not iso:
        return 0
    iso = tcslib.Iso(a.iso)
    gc2 = tcslib.GlyphCache(cs, iso)
    new = [(ch, p) for ch, p in cs.enc_pair.items()
           if tcslib.pair_slot(*p) >= 1504]
    print('    新 pair 条数 = %d' % len(new))
    no_ink = []
    for ch, p in sorted(new, key=lambda kv: tcslib.pair_slot(*kv[1]))[:5]:
        slot = tcslib.pair_slot(*p)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        ink = gc2._ink(x, y, x + 16, y + 16) if hasattr(gc2, '_ink') else None
        print('      %r %s slot %d 格 (%d,%d) 有字形=%s 墨=%s'
              % (ch, bytes(p).hex(' '), slot, x, y, gc2.has_glyph(ch), ink))
    for ch, p in new:
        if not gc2.has_glyph(ch):
            no_ink.append(ch)
    print('    ★ 368 个新字里"盘上无字形"的 = %d %s' % (len(no_ink), no_ink[:10]))
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
