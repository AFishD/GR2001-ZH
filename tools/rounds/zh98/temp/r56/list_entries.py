# -*- coding: utf-8 -*-
"""列出两个 IMG 的条目名 (抽查 #551..#565 与文本相关条目)。"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))
for tag, lba in (('MENU', 776286), ('GR', 19175)):
    print('==== %s.IMG' % tag)
    for idx in list(range(0, 40)) + list(range(545, 570)) + list(range(895, 910)):
        try:
            e = iso.img_entry(lba, idx)
        except Exception as ex:                                      # noqa: BLE001
            print('  #%d 读取失败 %s' % (idx, ex)); break
        if e['stored'] <= 0:
            print('  #%d 空' % idx); continue
        print('  #%-4d %-36s stored=%9d real=%9d' % (idx, e['name'], e['stored'], e['real']))
    for want in (25, 283):
        e = iso.img_entry(lba, want)
        print('  ★ #%d %-30s stored=%d' % (want, e['name'], e['stored']))
iso.close()
