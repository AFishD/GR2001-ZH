# -*- coding: utf-8 -*-
r"""probe_r63c.py — 跨盘对照 MENU.IMG#283 / GR.IMG#4058 的 stored/real/blob 演化。

GR_EN_ORIG (英文原盘) → GR_ZH98 → GR_ZH109: 看 real 是不是一直对不上 blob。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402

RXX = re.compile(r'(?:^|_)SPECIAL_FEATURE\.XML$', re.I)


def scan(path):
    print('\n== %s ==' % os.path.relpath(path, REPO).replace('\\', '/'))
    iso = T.Iso(path)
    for lba, imgn in ((T.MENU_LBA, 'MENU.IMG'), (T.GR_LBA, 'GR.IMG')):
        for idx in range(0, 6000):
            try:
                e = iso.img_entry(lba, idx)
            except Exception:                                          # noqa: BLE001
                break
            if not RXX.search(e['name'] or ''):
                continue
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs)
            ue = T.xml_tail_start(blob)
            print('  %-11s#%-5d %-28s stored=%-6d real=%-7d blob=%-7d sum=%-7d '
                  'real-blob=%+6d tail=%d  text=%d name=%d'
                  % (imgn, idx, e['name'], e['stored'], e['real'], len(blob),
                     sum(s[2] for s in subs), e['real'] - len(blob),
                     len(blob) - ue, len(T.TEXT_RE.findall(blob)),
                     len(re.findall(rb'<(?:studio|item|group)\b[^>]*name\s*=\s*"',
                                    blob))))
    iso.close()


def main():
    for ver in ('GR_EN_ORIG', 'GR_ZH98', 'GR_ZH109'):
        p = os.path.join(REPO, 'work', 'builds', ver, '%s.iso' % ver)
        if os.path.isfile(p):
            scan(p)


if __name__ == '__main__':
    main()
