# -*- coding: utf-8 -*-
r"""m26_slack.py — 量 3 个文本容器的压缩余量 (stored - 实际占用), 判断能否承受把 的/你 改成 2 字节码。
只读。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

for label, iso_p in (('GR_ZH92 (现役, 用户初译原文)', 'work/builds/GR_ZH92/GR_ZH92.iso'),
                     ('GR_ZH93 (当前, text_fix 替代文本)', 'work/builds/GR_ZH93/GR_ZH93.iso'),
                     ('FIXED (zh93 的字体基盘)', 'work/builds/GR_ZH93/temp/exp/FIXED.iso')):
    p = os.path.join(REPO, iso_p)
    if not os.path.exists(p):
        print('%s: 不存在' % label)
        continue
    iso = tcslib.Iso(p)
    print('== %s ==' % label)
    for (lba, idx, nm) in ((tcslib.MENU_LBA, 25, 'MENU#25 LANG'),
                           (tcslib.MENU_LBA, tcslib.XML_IDX, 'MENU#283 SFXML'),
                           (tcslib.GR_LBA, 902, 'GR#902 LANG')):
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        subs = tcslib.lzo_subs(raw)
        used = sum(8 + (s[1] if isinstance(s[1], int) else len(s[1])) for s in subs)
        real = sum(len(s[0]) for s in subs)
        print('  %-16s stored=%-7d real(展开)=%-7d 实际压缩占用=%-7d 余量=%-6d (%.1f%%)'
              % (nm, e['stored'], real, used, e['stored'] - used,
                 100.0 * (e['stored'] - used) / e['stored']))
    iso.close()
    print()
