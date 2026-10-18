# -*- coding: utf-8 -*-
r"""r57 普查: 每个容器展开态里"换码后文本会变"的字符数 —— 找还有哪里会显示乱码 (只读)。

口径: 同一个字节串, 旧 charset 解出 T1, 新 charset 解出 T2; 统计 T1≠T2 的字符数与其中
      汉字数。二进制数据本来就会"变"(引擎不按文本解它), 所以判读要看:**汉字多且变的多**。
"""
import os
import sys
import time

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
containers = FC.enumerate_containers(iso)
print('容器 %d 个; 逐容器统计 (旧解 vs 新解 的差异字符)' % len(containers))
KNOWN = {(FC.MENU_LBA, 283), (FC.MENU_LBA, 25), (FC.GR_LBA, 902)}
rows = []
t0 = time.time()
for k, (tag, lba, idx, e) in enumerate(containers):
    slot = FC.Slot(iso, tag, lba, idx)
    blob = slot.blob
    if not blob:
        continue
    t1, _ = old.decode(blob)
    t2, _ = new.decode(blob)
    ndiff = sum(1 for a, b in zip(t1, t2) if a != b)
    if not ndiff:
        continue
    cjk1 = sum(1 for c in t1 if '\u4e00' <= c <= '\u9fff')
    cjkdiff = sum(1 for a, b in zip(t1, t2)
                  if a != b and ('\u4e00' <= a <= '\u9fff' or '\u4e00' <= b <= '\u9fff'))
    rows.append((cjkdiff, ndiff, cjk1, tag, idx, e['name'], len(blob),
                 (lba, idx) in KNOWN, slot.mode))
rows.sort(reverse=True)
print('有差异的容器 %d 个; %.1fs' % (len(rows), time.time() - t0))
print('\n按"换码后汉字会变"降序 (前 30):')
print('  %-9s %-9s %-8s %-26s %-10s %s' % ('汉字变了', '字符变了', '旧汉字数', '容器', '大小', '已知文本容器'))
for r in rows[:30]:
    print('  %-9d %-9d %-8d %-26s %-10d %s'
          % (r[0], r[1], r[2], '%s#%d %s' % (r[3], r[4], r[5]), r[6],
             '★已知' if r[7] else ('(raw)' if r[8] == 'raw' else '')))
print('\n一个字符都不变的容器: %d' % (len(containers) - len(rows)))
iso.close()
