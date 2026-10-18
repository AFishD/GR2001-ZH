# -*- coding: utf-8 -*-
r"""r57 探针6: MENU.IMG#30 EN_STRINGS.TXT 里那 8 条"会变味"的串是哪几行 / 键是什么? (只读)"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
new = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_after_r56.json'))
iso = tcslib.Iso(ISO)
tag, lba, idx, e = [c for c in FC.enumerate_containers(iso) if c[1] == FC.MENU_LBA
                    and c[2] == 30][0]
slot = FC.Slot(iso, tag, lba, idx)
blob = slot.blob
print('MENU.IMG#30 %s: 槽 %d B, 模式 %s, 展开 %d B, 首 60B=%r'
      % (e['name'], slot.slot, slot.mode, len(blob), blob[:60]))
txt = blob.split(b'\r\n')
n = 0
for ln in txt:
    if b'"' not in ln:
        continue
    a = old.decode(ln)[0]
    b = new.decode(ln)[0]
    if a != b:
        n += 1
        print('  ----> 旧 %r' % a)
        print('        新 %r' % b)
        print('        raw %s' % ln[:110])
        if n >= 12:
            break
print('共 %d 行会变味 (前 12 行已列出)' % n)
iso.close()
