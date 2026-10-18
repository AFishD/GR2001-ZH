# -*- coding: utf-8 -*-
r"""check_protected_ranges.py — 逐条证明"敏感区域"不在差异集合里 (不是靠"我没碰"的口头保证)。

对每个"必须逐字节不变"的区域, 算出它在 ISO 里的字节区间, 与差异区间的**并集**求交 —— 交集必须为空:
  · ELF (ISO LBA 295 起, 程序代码)
  · MENU.IMG 的**条目表**(头部) + GR.IMG 的**条目表**(头部)
  · GR.IMG 第 551..565 条 (制作组名单那一段)
  · COMMON.PAK 的 48B 包头 + PAK 头 (像素容器之前的部分)
  · 3 个文本容器的槽区 (EN_STRINGS.RES@MENU / @GR / EN_SPECIAL_FEATURE.XML)
  · 制作组名单以外的 GR.IMG 条目表区间
  · ISO 的 PVD / 卷描述符

用法: python check_protected_ranges.py <A.iso> <B.iso> <diff.json>
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                       # noqa: E402


def main():
    a = sys.argv[1:]
    A, B, dj = a[0], a[1], a[2]
    doc = json.load(io.open(dj, encoding='utf-8'))
    diff = set()
    for r in doc['ranges']:
        for o in range(r['off0'], r['off1'] + 1):
            diff.add(o)
    print('差异字节集合: %d 个 (来自 %s)' % (len(diff), os.path.basename(dj)))

    iso = tcslib.Iso(A)
    regions = []
    regions.append(('ELF (程序, LBA 295 起 1 MB)', 295 * 2048, 295 * 2048 + (1 << 20)))
    regions.append(('ISO PVD + 卷描述符 (LBA 16..19)', 16 * 2048, 20 * 2048))
    regions.append(('MENU.IMG 条目表头部 (前 24 条 × 3 个表)',
                    tcslib.MENU_LBA * 2048, tcslib.MENU_LBA * 2048 + 0x4000))

    # IMG 的**条目表**本体 (每个条目的 off/stored 字段就在 IMG 最前面那几 KB)
    for lba, nm in ((tcslib.MENU_LBA, 'MENU.IMG'), (tcslib.GR_LBA, 'GR.IMG')):
        regions.append(('%s 条目表本体 (IMG 起始 0x4000 B)' % nm,
                        lba * 2048, lba * 2048 + 0x4000))

    # GR.IMG 551..565 (制作组名单)
    for i in range(551, 566):
        e = iso.img_entry(tcslib.GR_LBA, i)
        if e:
            regions.append(('GR.IMG #%d %s (制作组名单段)' % (i, e['name']),
                            e['iso_off'], e['iso_off'] + e['stored']))

    # COMMON.PAK 像素容器之前的部分 (PAK 头 + 48B 包头的容器前缀)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e and e['name'] == 'COMMON.PAK':
            pak_e = e
        if e and e['name'] == 'FONT.RES':
            ft_e = e
    if pak_e:
        regions.append(('COMMON.PAK 头部 (像素容器之前)',
                        pak_e['iso_off'], doc['container']['c0']))
        regions.append(('COMMON.PAK 像素容器之后到条目末尾 (PAK 包头/其余数据)',
                        doc['container']['c1'], pak_e['iso_off'] + pak_e['stored']))
    if ft_e:
        regions.append(('FONT.RES 全部 (FT 记录表)',
                        ft_e['iso_off'], ft_e['iso_off'] + ft_e['stored']))
    iso.close()

    print('')
    bad = 0
    for name, lo, hi in regions:
        n = len([o for o in range(lo, hi) if o in diff])
        flag = 'OK ' if n == 0 else '!! '
        if n:
            bad += 1
        print('  %s%-58s [0x%09X,0x%09X) 差异 %d' % (flag, name, lo, hi, n))
    print('')
    print('**被证明"逐字节不变"的敏感区域: %d 个; 其中含差异的: %d 个**'
          % (len(regions), bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
