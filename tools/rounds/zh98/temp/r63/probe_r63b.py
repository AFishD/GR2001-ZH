# -*- coding: utf-8 -*-
r"""probe_r63b.py — IMG 条目 real 字段 vs 解压总长的关系 (10 份 SFXML 副本 + LANG)。

只读 GR_ZH109.iso。判据: 引擎若按条目表 real 分配缓冲区, 则解压总长**不能变**;
若 real 普遍对不上 (陈旧), 说明引擎按 LZO 子流头逐个解压 ⇒ 可放宽。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import inject_text_csv as inj                                         # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')


def show(iso, tag, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = T.lzo_subs(raw)
    blob = b''.join(s[0] for s in subs)
    ue = T.xml_tail_start(blob)
    print('%-46s stored=%-6d real=%-7d blob=%-7d sum=%-7d real-blob=%+6d frames=%d '
          'tail=%d  name=%s'
          % (tag, e['stored'], e['real'], len(blob), sum(s[2] for s in subs),
             e['real'] - len(blob), len(subs), len(blob) - ue, e['name']))


def main():
    iso = T.Iso(ISO)
    print('== SFXML 10 份副本 ==')
    for (img, lba, idx, tag) in T.RES['SFXML']['copies']:
        show(iso, tag, lba, idx)
    import re
    print('\n== 同一 IMG 里所有 SPECIAL_FEATURE.XML (r62 报告的 10 份) ==')
    rxx = re.compile(r'(?:^|_)SPECIAL_FEATURE\.XML$', re.I)
    for lba, imgn in ((T.MENU_LBA, 'MENU.IMG'), (T.GR_LBA, 'GR.IMG')):
        for idx in range(0, 6000):
            try:
                e = iso.img_entry(lba, idx)
            except Exception:                                          # noqa: BLE001
                break
            if e['stored'] <= 0 or not e['name']:
                break
            if rxx.search(e['name']):
                show(iso, '%s#%d' % (imgn, idx), lba, idx)
    print('\n== LANG 两份 ==')
    for (img, lba, idx, tag) in T.RES['LANG']['copies']:
        show(iso, tag, lba, idx)
    iso.close()


if __name__ == '__main__':
    main()
