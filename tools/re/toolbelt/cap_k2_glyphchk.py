# -*- coding: utf-8 -*-
r"""cap_k2_glyphchk.py -- 借槽字形与手绘件的前置检查 (只读)

  ① glyph_handoff.json 的 4 个 bitmap vs 基底盘对应记录矩形的墨 (逐 texel)
  ② 基底盘槽 1504 (r84 手绘 △) 的墨图案 (给自制 ✕ 定风格)
  ③ 盘上有没有现成的 '✕/×/X' 类字形可复用 (charset 里查 char, 再取它的槽)
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

HANDOFF = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'temp', 'handoff',
                       'glyph_handoff.json')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip):
    return 2 + 16 * (row + (skip if row >= 12 else 0))


def main():
    iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso'))
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e['iso_off'], e['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _c = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    iso.close()
    P('基底 %dx%d' % (rec[2], rec[3]))
    h = json.load(io.open(HANDOFF, encoding='utf-8'))
    P('handoff: gate=%s target_geometry=%s items=%d'
      % (h['gate'], h['target_geometry'], len(h['items'])))
    ok = 0
    for it in h['items']:
        code, ch, ri = it['code'], it['char'], it['record_index']
        r = it['record']
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        bm = np.array(it['bitmap'], dtype=int)
        base_ink = img[v0:v1, u0:u1]
        if bm.shape != base_ink.shape:
            P('  %s %-3s rec#%d rect=(%d,%d,%d,%d) %s bitmap %s ≠ rect %s'
              % (code, ch, ri, u0, v0, u1, v1, '✗', bm.shape, base_ink.shape))
            continue
        # bitmap 的 0 与 1 两种口径都试
        as_ink0 = (bm == 0)
        as_ink1 = (bm == 1)
        eq0 = bool((as_ink0 == base_ink).all())
        eq1 = bool((as_ink1 == base_ink).all())
        P('  %s %-3s rec#%d rect=(%d,%d,%d,%d) %dx%d 墨=%d | bitmap==基底: 0为墨=%s / 1为墨=%s'
          % (code, ch, ri, u0, v0, u1, v1, u1 - u0, v1 - v0, int(base_ink.sum()),
             eq0, eq1))
        if eq0 or eq1:
            ok += 1
    P('⇒ handoff bitmap 与基底逐 texel 相同的条目: %d / %d' % (ok, len(h['items'])))
    # ② 槽 1504 (r84 手绘 △)
    for s in (1504, 1505):
        row, col = s // 62, s % 62
        x, y = 16 * col, yrow(row, 3)
        g = img[y:y + 16, x:x + 16]
        P('')
        P('[slot %d] 老布局格 (%d,%d) 墨 %d' % (s, x, y, int(g.sum())))
        for i in range(16):
            P('    |' + ''.join('#' if g[i, k] else '.' for k in range(16)))
    # ③ 现成的 ✕ 类字形
    cs = json.load(io.open(T.CHARSET, encoding='utf-8'))
    P('')
    P('③ charset 里与 ✕/×/X 有关的字符:')
    for cand in ('\u2715', '\u00d7', '\u2716', '\u2573', 'X', 'x', '\u4e58', '\u53c9',
                 '\u274c', '\u00d7'):
        if cand in cs['pair_of']:
            pr = cs['pair_of'][cand]
            slot = (pr[0] - 0xA1) * 94 + (pr[1] - 0xA1)
            P('    %r U+%04X → pair %02X%02X slot=%d' % (cand, ord(cand), pr[0], pr[1], slot))
        elif cand in cs['codes']:
            P('    %r U+%04X → 单字节 0x%02X' % (cand, ord(cand), cs['codes'][cand]))
        else:
            P('    %r U+%04X → 不在 charset' % (cand, ord(cand)))
    out = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp', 'k2_glyphchk.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
