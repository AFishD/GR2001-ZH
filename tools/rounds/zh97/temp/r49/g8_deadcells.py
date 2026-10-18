# -*- coding: utf-8 -*-
r"""g8_deadcells.py — 144 个死字的格子 vs FT 膨胀窗: 到底有几个格、多少 px 相碰?"""
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
import font_residue as FR                                            # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
DEAD = ('µ丁丹丽乔亨伟伯佐俊傅兰冈凡刘勃卜历史叶吕吴哥哲唐圣坤培夏奈奋姚娜娱孙宁宇宋宗富岩峰廉弗彭彼徐怀思恩戈戴扬斌斐昂晓曹朱李杜杨杰柯柴桑楠欣欧歇殷毅毕汀汤沈洛津洪浩滕潘熊玉'
        '王玲珀珊珍琳琼瑞瑟皮督福穆缪罕翁翔翰耶肖舒艾芬茨荣莉莱菲葆蒂蒙蓓蔡蕾袁裁詹费贾赖辉辛迈逊邹郑闫阮阳陈隆雅霍韦魏鲍鹏麦黛')


def main():
    res = FR.compute(ISO, verbose=False)
    ink = res['atlas'].eng
    ft_dil = res['sampler']['ft_dil']
    ft_raw = res['sampler']['ft_raw']
    cs = res['cs']
    bad, raw_bad, tot_over = [], [], 0
    for ch in DEAD:
        b1, b2 = cs.enc_pair[ch]
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        cell_dil = ft_dil[y:y + 16, x:x + 16]
        cell_raw = ft_raw[y:y + 16, x:x + 16]
        n_cell = int((ink[y:y + 16, x:x + 16]).sum())
        if cell_dil.any():
            n = int(cell_dil.sum())
            tot_over += n
            bad.append((ch, slot, slot // 62, slot % 62, x, y, n, n_cell,
                        int(cell_raw.sum())))
        if cell_raw.any():
            raw_bad.append((ch, slot, int(cell_raw.sum())))
    print('144 个死字里, 格子与 **膨胀窗(±4,2)** 相碰的: %d 个; 相碰像素合计 %d' % (len(bad), tot_over))
    print('其中与 **原矩形**(repack 口径) 相碰的: %d 个' % len(raw_bad))
    for (ch, slot, r, c, x, y, n, n_cell, n_raw) in bad:
        print('  %s slot=%4d 行%2d 列%2d cell=(%d,%d) 膨胀窗压住 %d px (该格共 %d px 墨; 原矩形压 %d px)'
              % (ch, slot, r, c, x, y, n, n_cell, n_raw))
    print('')
    print('⇒ 若"保留膨胀窗内的像素", 受影响格数 = %d; 直接可用的新格 = 90 + (144 − %d) = %d'
          % (len(bad), len(bad), 90 + 144 - len(bad)))


if __name__ == '__main__':
    main()
