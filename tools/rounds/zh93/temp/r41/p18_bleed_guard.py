# -*- coding: utf-8 -*-
r"""p18_bleed_guard.py — 「引擎格有墨」这个判据会不会被**相邻行的 1 行渗漏**骗到?

背景: 回绕列的字形比 yrow 低 1 行 ⇒ 它最后一行落在**下一行 cell 的第 0 行**。
于是"下一行"的 cell 里会出现 1 行不属于自己的墨 ⇒ `ink > 0` 会误判成"有字形"。

本脚本测两件事:
  A) 现役盘 GR_ZH93 上 1319 个对偶字: 把 cell 的**第 0 行剔掉**后 (只看 1..15 行) 还剩多少墨?
     若全部 > 0 ⇒ 用「1..15 行有墨」当判据是安全的 (不会误杀真字形)。
  B) 延 (ADF1) 在 GR_ZH92 / GR_ZH93 上两种判据的结论。
  C) 旧 charset 备份里 延 的码位 (解释它为什么"搬过家")。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                  # noqa: E402
import tcslib                                                       # noqa: E402

W, H = 1024, 512
BAK = os.path.join(REPO, 'work', '_planc', 'charset_before_planc.json')


def atlas_of(name):
    p = os.path.join(REPO, 'work', 'builds', name, name + '.iso')
    iso = tcslib.Iso(p)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    _nm, psm, w, h, clut, px_size, PX = [r for r in tcslib.parse_pak_records(pak)
                                         if r[0] == 'new_font_revised'][0]
    nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    return (A == 0)


def main():
    cs = tcslib.Charset()
    if os.path.isfile(BAK):
        old = json.load(io.open(BAK, encoding='utf-8'))
        print('[C] 旧 charset 备份 %s:' % os.path.relpath(BAK, REPO))
        for ch in '延志普略米欣袁':
            o = old.get('pair_of', {}).get(ch)
            n = cs.enc_pair.get(ch)
            print('    %s: 旧 pair=%s  现 pair=%s  %s'
                  % (ch, ('%02X%02X' % tuple(o)) if o else '无',
                     ('%02X%02X' % tuple(n)) if n else '无',
                     '★ 码位搬过家' if o and n and tuple(o) != tuple(n) else ''))
    else:
        print('[C] 找不到旧 charset 备份, 跳过')

    for name in ('GR_ZH92', 'GR_ZH93'):
        ink = atlas_of(name)
        print('\n===== %s =====' % name)
        # A) 1319 个对偶字: cell 全墨 vs 去掉第 0 行
        n0_all, n0_skip0, worst = 0, 0, []
        for ch, (b1, b2) in cs.enc_pair.items():
            x, y = tcslib.atlas_cell_xy_engine(tcslib.pair_slot(b1, b2))
            a = int(ink[y:y + 16, x:x + 16].sum())
            b = int(ink[y + 1:y + 16, x:x + 16].sum())
            if a == 0:
                n0_all += 1
            if b == 0:
                n0_skip0 += 1
                worst.append((ch, a, b, x, y))
        print('  [A] 判据「cell 有墨(含第0行)」判定无字形的: %d 个' % n0_all)
        print('      判据「cell 的 1..15 行有墨」判定无字形的: %d 个' % n0_skip0)
        for ch, a, b, x, y in worst[:15]:
            print('        %s cell(%d,%d) 全墨=%d 去第0行=%d' % (ch, x, y, a, b))
        # B) 延
        s = tcslib.pair_slot(*cs.enc_pair['延'])
        x, y = tcslib.atlas_cell_xy_engine(s)
        print('  [B] 延 引擎格(%d,%d): 全墨=%d  去第0行=%d  ⇒ 「有字形」? %s'
              % (x, y, int(ink[y:y + 16, x:x + 16].sum()),
                 int(ink[y + 1:y + 16, x:x + 16].sum()),
                 '是' if ink[y + 1:y + 16, x:x + 16].sum() else '否'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
