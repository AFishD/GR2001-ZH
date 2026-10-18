# -*- coding: utf-8 -*-
r"""r58 探针3: MENU.IMG#30 EN_STRINGS.TXT (旧解) 与 MENU.IMG#25 EN_STRINGS.RES (新解) 的同一批键对照。

目的: 确认 EN_STRINGS.TXT 里的陈旧字节用**旧 charset** 解出来是不是"原字" (Lead 点名的
      传感器/无限制/亲手枪), 以及和可注入的 LANG 表 (已是新码) 是否一致。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

CS_OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
CS_NEW = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
old = tcslib.Charset(CS_OLD)
new = tcslib.Charset(CS_NEW)
iso = tcslib.Iso(ISO107)


def blob(tag, idx):
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    return FC.Slot(iso, tag, lba, idx).blob


txt_blob = blob('MENU.IMG', 30)
t_old = old.decode(txt_blob)[0]
t_new = new.decode(txt_blob)[0]
print('=== MENU.IMG#30 EN_STRINGS.TXT 全文 (旧解; 只打可见行) ===')
for ln in t_old.split('\r\n'):
    if ln.strip():
        print('   %r' % ln)

print('\n=== 逐行: 旧解 vs 新解 (只打两者不同的行) ===')
for a, b in zip(t_old.split('\r\n'), t_new.split('\r\n')):
    if a != b:
        print('   旧 %r' % a)
        print('   新 %r' % b)

print('\n=== 同一批键在 MENU.IMG#25 EN_STRINGS.RES (新码, 可注入) 里的值 ===')
ents, _ = tcslib.parse_lang(blob('MENU.IMG', 25))
want = set(re.findall(r'"(WPN_[A-Z0-9_]+|ITM_[A-Z0-9_]+)"', t_old))
keys = re.findall(r'"([A-Za-z0-9_]+)"\s*\r?\n?\s*\t+"([^"]*)"', t_old)
print('   (TXT 里成对的键→中文: %d 对)' % len(keys))
byc = {}
for en in ents:
    t = new.decode(en.data)[0]
    if t:
        byc.setdefault(t, []).append(en)
for (k, v) in keys:
    hit = None
    for en in ents:
        t = new.decode(en.data)[0]
        if t == v:
            hit = (en.g, en.i, t)
            break
    print('   %-22s TXT(旧解) %-14r  → RES 里同值条目: %s' % (k, v, hit))
iso.close()
