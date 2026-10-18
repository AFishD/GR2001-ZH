# -*- coding: utf-8 -*-
r"""cap_k2_iconchk.py -- 只读: FONT.RES 槽尾部零填充核对 + 两个硬编码图标区的墨图案
(给自制 16x16 ✕ 定风格的参考; 并核对图标区不得被搬动的墨污染)
"""
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


def P(*a):
    print(' '.join(str(x) for x in a), flush=True)


def main():
    iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso'))
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    e_ft = [x for x in ent if x['name'] == 'FONT.RES'][0]
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    subs = T.lzo_subs(ft_slot)
    olen = subs[0][1]
    frame = ft_slot[:8 + olen]
    tail = ft_slot[8 + olen:]
    P('[ft] 槽 %d B ; stored=%d real=%d ; 子流 %d 个 comp=%d real=%d ; 帧 %d B'
      % (len(ft_slot), e_ft['stored'], e_ft['real'], len(subs), subs[0][1], subs[0][2],
         len(frame)))
    P('[ft] 尾部 %d B 全零: %s' % (len(tail), all(b == 0 for b in tail)))
    nz = [i for i, b in enumerate(tail) if b]
    P('[ft] 尾部非零字节数: %d %s' % (len(nz), nz[:8]))
    # 图标区
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _c = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    iso.close()
    for (x0, y0, x1, y1, nm) in ((1, 198, 21, 218, '0xB5 ✕ 叉键 (UV 1,198-21,218)'),
                                 (25, 198, 45, 218, '0xB1 △ 三角键 (UV 25,198-45,218)')):
        sub = img[y0:y1, x0:x1]
        P('')
        P('[icon] %s  %dx%d 墨 %d' % (nm, x1 - x0, y1 - y0, int(sub.sum())))
        for i in range(y1 - y0):
            P('    |' + ''.join('#' if sub[i, k] else '.' for k in range(x1 - x0)))
    # 哪个记录/没有主 覆盖图标区
    ft = b''.join(s[0] for s in subs)
    faces, _e = zx_lib.ft_records(ft, 28)
    P('')
    P('[own] 覆盖图标区的记录窗:')
    for (fn, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] <= r[2] or r[5] <= r[3]:
                continue
            for (x0, y0, x1, y1, nm) in ((1, 198, 21, 218, 'cross'), (25, 198, 45, 218, 'tri')):
                if r[2] < x1 and x0 < r[4] and r[3] < y1 and y0 < r[5]:
                    P('    %-8s #%-4d 0x%02X rect=(%4d,%3d,%4d,%3d) 与 %s 相交'
                      % (fn, k, k + 0x20, r[2], r[3], r[4], r[5], nm))
    return 0


if __name__ == '__main__':
    sys.exit(main())
