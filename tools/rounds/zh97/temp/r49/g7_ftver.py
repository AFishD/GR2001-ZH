# -*- coding: utf-8 -*-
r"""g7_ftver.py — 校验 FT 记录表被**完整**解析 (nfaces / 记录数 / 解析是否吃满整个文件)。

如果 FT 表里还有没被解析到的 face 或记录, font_residue 的"采样窗"就不完整。
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')


def main():
    font = dump_font.load_font(ISO)
    ft = font['ft_blob']
    print('FONT.RES 展开态长度 = %d B (槽 %d B)' % (len(ft), len(font['ft_slot'])))
    n = struct.unpack_from('<I', ft, 24)[0]
    print('nfaces (偏移 24) = %d' % n)
    p, faces = tcslib.parse_ft_faces(ft)
    print('解析到 %d 个 face, 吃掉 %d B / 共 %d B' % (len(faces), p, len(ft)))
    print('尾部剩余字节 = %d' % (len(ft) - p))
    tot = 0
    for (nm, fld, recs) in faces:
        ne = sum(1 for r in recs if r[4] > r[2] and r[5] > r[3])
        tot += ne
        print('  face %-10s fld[4..5]=%s nrec=%d 非空=%d' % (nm, fld[4:6], len(recs), ne))
    print('非空记录合计 = %d' % tot)
    # 把 FONT.RES 在盘上的位置与长度也报出来
    e = font['pak_e']
    print('pak entry: %s off=0x%X stored=%d' % (e['name'], e['iso_off'], e['stored']))
    for i in range(24):
        iso = tcslib.Iso(ISO)
        x = iso.img_entry(tcslib.MENU_LBA, i)
        iso.close()
        if x and x['name'] == 'FONT.RES':
            print('MENU.IMG #%d FONT.RES off=0x%X stored=%d' % (i, x['iso_off'], x['stored']))
    print('')
    print('font dict keys: %s' % sorted(font.keys()))
    print('ft_from = %s' % font.get('ft_off'))


if __name__ == '__main__':
    main()
