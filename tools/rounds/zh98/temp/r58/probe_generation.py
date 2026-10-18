# -*- coding: utf-8 -*-
r"""r58 探针4: EN_STRINGS.TXT (MENU.IMG#30) 的陈旧字节到底是**哪一代** charset 写下的?

做法: 拿仓库里能找到的所有 charset 快照, 逐个解 EN_STRINGS.TXT, 打印那 8 条引号串
      (WPN_EXTRAAMMO / ITM_BINOCULARS / ITM_SENSOR / ITM_BOMB / No Restrictions /
       Pistols Only / Primary Weapons Only / Originals Only), 看哪一代最像人话。
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
KEYS = ['WPN_EXTRAAMMO', 'ITM_BINOCULARS', 'ITM_SENSOR', 'ITM_CLAYMORE', 'ITM_BOMB',
        'No Restrictions', 'Pistols Only', 'Primary Weapons Only', 'Originals Only',
        'Standard Kits']
PAIRS = re.compile(r'"([^"]+)"[\t\r\n ]+"([^"]*)"')

iso = tcslib.Iso(ISO107)
blob = FC.Slot(iso, 'MENU.IMG', FC.MENU_LBA, 30).blob
iso.close()

snaps = sorted(set(glob.glob(os.path.join(REPO, 'work', '**', 'charset*.json'), recursive=True)
                   + glob.glob(os.path.join(REPO, 'tools', '**', 'charset*.json'), recursive=True)))
for p in snaps:
    try:
        cs = tcslib.Charset(p)
    except Exception as e:                                            # noqa: BLE001
        print('%-70s 读不出: %s' % (os.path.relpath(p, REPO), e))
        continue
    t, _ = cs.decode(blob)
    m = {}
    for a, b in PAIRS.findall(t):
        m[a] = b
    got = [('%s=%s' % (k, m[k])) for k in KEYS if k in m and m[k] != k]
    n_cjk = sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff')
    print('%-72s 汉字%5d  | %s' % (os.path.relpath(p, REPO), n_cjk, '  '.join(got)))
