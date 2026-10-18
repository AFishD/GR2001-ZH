# -*- coding: utf-8 -*-
"""r51 探针⑪: EN_SPECIAL_FEATURE.XML 里 T0063 附近的**原始结构** —— 标题到底存在哪个字段? 只读。"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
iso = tcslib.Iso(ISO)
# 找 EN_SPECIAL_FEATURE.XML 所在的条目
found = None
for lba_name, n in (('GR.IMG', None),):
    pass
# 用工程现成口径: 直接按名字扫 ISO 里的 IMG 条目
hits = []
for lba in tcslib.RES.get('IMG_LBAS', []) or []:
    pass
print('tcslib.RES keys: %s' % list(tcslib.RES.keys()))
for k, v in tcslib.RES.items():
    print('   %s = %r' % (k, v))
