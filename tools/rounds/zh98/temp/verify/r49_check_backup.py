# -*- coding: utf-8 -*-
r"""r49_check_backup.py — 抽验"死字回收是可还原的": 用备份里的位图重建字形, 与 GR_ZH97 盘上逐像素比。

同时验证:
  · 备份里 144 个字的码位/格子 与 `charset_before_font_cleanup.json` 的 pair_of 完全一致;
  · 每个字的位图与 **GR_ZH97** 盘上那一格逐像素相同 (说明备份是真能还原的);
  · 每个字的位图与 **GR_ZH98** 盘上那一格**全空** (说明确实擦干净了)。
"""
import base64
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402

B = os.path.join(REPO, 'work', 'builds', 'GR_ZH98')
ISO97 = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
ISO98 = os.path.join(B, 'GR_ZH98.iso')


def atlas_of(iso):
    f = dump_font.load_font(iso)
    a = f['atlas']
    return repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm'])


def main():
    bak = json.load(io.open(os.path.join(B, 'temp', 'font_recycle_backup.json'), encoding='utf-8'))
    cs0 = json.load(io.open(os.path.join(B, 'temp', 'charset_before_font_cleanup.json'),
                            encoding='utf-8'))
    cs1 = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                         'charset_compiled_zh16.json'), encoding='utf-8'))
    print('备份: %d 个字 (%s)' % (bak['count'], bak['chars']))
    print('charset: before %d 条 → after %d 条' % (len(cs0['pair_of']), len(cs1['pair_of'])))
    miss = [c for c in bak['chars'] if c in cs1['pair_of']]
    print('  仍留在 charset 里的死字: %d 个 %s' % (len(miss), ''.join(miss)))
    print('  charset 里 _font_recycle_zh98.removed = %s'
          % (cs1.get('_font_recycle_zh98', {}) or {}).get('removed'))
    A97 = atlas_of(ISO97)
    A98 = atlas_of(ISO98)
    bad_pair = bad97 = bad98 = 0
    for ch, g in bak['glyphs'].items():
        want_pair = cs0['pair_of'][ch]
        if list(want_pair) != list(g['pair']):
            bad_pair += 1
        x, y = g['cell']
        bits = np.unpackbits(np.frombuffer(base64.b64decode(g['bits']), np.uint8))
        ref = bits.reshape(16, 16).astype(bool)
        if not np.array_equal(A97.eng[y:y + 16, x:x + 16], ref):
            bad97 += 1
            print('  !! %s 备份位图与 GR_ZH97 盘上不一致' % ch)
        if A98.eng[y:y + 16, x:x + 16].any():
            bad98 += 1
            print('  !! %s 的格子在 GR_ZH98 上还有墨' % ch)
    print('')
    print('码位一致: %d/%d 不符' % (bad_pair, bak['count']))
    print('位图与 GR_ZH97 逐像素相同: %d/%d 不符' % (bad97, bak['count']))
    print('GR_ZH98 上那些格子已全空: %d/%d 不符' % (bad98, bak['count']))
    ok = not (miss or bad_pair or bad97 or bad98)
    print('⇒ %s' % ('全部通过: 144 个死字的字形可从备份原样还原, 且新盘上确实擦干净了'
                    if ok else '有问题, 见上面 !!'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
