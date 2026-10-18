# -*- coding: utf-8 -*-
r"""r57 探针4: GR.IMG 那个 6 MB "未分配空隙" 里的文本, 换码前后是否变了? (只读)"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_before_r56.json'))
new = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                 'charset_after_r56.json'))
iso = tcslib.Iso(ISO)
LO, HI = 0x1F035800, 0x1F635800
data = bytes(iso.mm[LO:HI])
print('区间 %d B (%.1f MB)' % (len(data), len(data) / 1e6))
t1, _ = old.decode(data)
t2, _ = new.decode(data)
diff = sum(1 for a, b in zip(t1, t2) if a != b)
print('旧解 vs 新解: 字符 %d, **不同 %d** (%.4f%%)' % (len(t1), diff, 100.0 * diff / len(t1)))
cjk1 = sum(1 for c in t1 if '\u4e00' <= c <= '\u9fff')
cjk2 = sum(1 for c in t2 if '\u4e00' <= c <= '\u9fff')
print('汉字数: 旧 %d / 新 %d' % (cjk1, cjk2))
# 逐行看: 把可打印行切出来
import re                                                              # noqa: E402
txt = data.split(b'\x00')
lines = [x for x in txt if len(x) > 6 and x.count(b'"') >= 2]
print('含引号的行 %d 条; 前 8 条:' % len(lines))
bad = 0
for ln in lines[:8]:
    a, _ = old.decode(ln)
    b, _ = new.decode(ln)
    same = (a == b)
    bad += (not same)
    print('   %-56r 旧=%r 新=%r %s' % (ln[:56], a[:40], b[:40], '' if same else '★变了'))
nsame = 0
for ln in lines:
    a, _ = old.decode(ln)
    b, _ = new.decode(ln)
    nsame += (a != b)
print('全部 %d 行里, 换码后**文本变了**的: %d 行' % (len(lines), nsame))
iso.close()
