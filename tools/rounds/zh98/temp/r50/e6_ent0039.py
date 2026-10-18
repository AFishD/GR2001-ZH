# -*- coding: utf-8 -*-
"""r50: 用英文解码器直接读 GR_EN_ORIG 的 SFXML 容器, 打印 T0039 的原文。

这是**独立于中文盘**的一条读取路径 (tcslib.en_read_tables + decode_en),
用来核实「中文译文里的 ± 对应的英文原文是什么」。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                             # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso'))
try:
    lang, sfxml, info = tcslib.en_read_tables(iso, verify_copies=True)
    print('EN LANG 非空条目 %d, SFXML 非空条目 %d, 拷贝不一致 %s'
          % (info['lang']['nonempty'], info['sfxml']['nonempty'],
             info['copies_differ'] or '无'))
    print('SFXML:T0039 原文 (%d B):' % len(sfxml.get('SFXML:T0039', '')))
    print('   ', repr(sfxml.get('SFXML:T0039')))
    print('EN 盘字节直方图 (SFXML):', tcslib.fmt_en_hist(info['sfxml']['bytes'])[:400])
    print('EN 盘字节直方图 (LANG)  :', tcslib.fmt_en_hist(info['lang']['bytes'])[:400])
finally:
    iso.close()
