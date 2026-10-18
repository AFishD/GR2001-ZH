# -*- coding: utf-8 -*-
"""细查: ① SFXML 的干净段 (为什么只 1 段?) ② NTSC_IKE.RES / IKE.RES 到底是什么。"""
import io
import os
import re
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
from scan2 import clean_runs                                          # noqa: E402

cs = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))


def blob_of(lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = tcslib.lzo_subs(raw)
    return e, (b''.join(s[0] for s in subs) if subs else raw)


e, blob = blob_of(776286, 283)
print('==== SFXML blob %d B  %s' % (len(blob), e['name']))
runs = clean_runs(blob, cs, min_cjk=1)
print('干净段 (min_cjk=1): %d 段' % len(runs))
for (a, b, t, best) in runs[:25]:
    print('   off=%-7d len=%-5d maxcjk=%-3d %r' % (a, b - a, best, t[:80]))
print('   ...')
# name= 属性逐个看
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
bad = 0
for m in NAME.finditer(blob):
    v = m.group(1)
    t, _ = cs.decode(v)
    if any('\u4e00' <= c <= '\u9fff' for c in t):
        ok = True
        for ch in v:
            if ch >= 0x80:
                pass
        bad += 1
        if bad <= 6:
            print('   name 属性 @%-7d %-40r %s' % (m.start(1), t[:30], v[:14].hex(' ')))
print('   含中文的 name 属性: %d' % bad)
# 检查这些属性字节能否"干净解析"
for m in list(NAME.finditer(blob))[:6]:
    v = m.group(1)
    rr = clean_runs(v, cs, min_cjk=1)
    print('   属性 %-24r → 干净段 %d, 文本 %r' % (v[:12].hex(' '), len(rr),
                                                rr[0][2] if rr else ''))

for (tag, lba, idx) in (('NTSC_IKE.RES', 776286, 282), ('IKE.RES', 19175, 909)):
    e, blob = blob_of(lba, idx)
    print('==== %s %s @%s#%d  stored=%d real=%d blob=%d' % (tag, e['name'], lba, idx,
                                                            e['stored'], e['real'], len(blob)))
    print('   头 64 B: %s' % blob[:64].hex(' '))
    runs = clean_runs(blob, cs, min_cjk=4)
    print('   干净 ≥4 汉字段: %d 段; 最长 %d' % (len(runs), max((r[3] for r in runs), default=0)))
    for r in sorted(runs, key=lambda x: -x[3])[:8]:
        print('     off=%-7d len=%-5d maxcjk=%-3d %r' % (r[0], r[1] - r[0], r[3], r[2][:70]))
iso.close()
