# -*- coding: utf-8 -*-
r"""fix_zh116_entries.py — 对比各代盘 MENU.IMG / GR.IMG 条目布局 vs 英文原盘

判据 (docs/PROGRESS.md §51): 游戏对 GR.IMG 某些条目有**硬编码偏移访问**;
条目 off/stored 与原盘不同 ⇒ 读档/进关卡卡死。

用法:
  python tools/iso_build/fix_zh116_entries.py [--versions GR_ZH98,...] [--control GR_EN_ORIG]
"""
import argparse
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMGS = {'MENU.IMG': 776286, 'GR.IMG': 19175}


def iso_entries(path, lba):
    with open(path, 'rb') as f:
        f.seek(lba * SEC + 0x10)
        noff, nend = struct.unpack('<II', f.read(8))
        f.seek(lba * SEC + noff)
        names = [x.decode('latin-1') for x in f.read(nend - noff).split(b'\x00') if x]
        f.seek(lba * SEC + TAB_OFF)
        raw = f.read(TAB_STEP * len(names))
    ents = {}
    for i, nm in enumerate(names):
        e = list(struct.unpack_from('<12I', raw, TAB_STEP * i))
        ents[nm] = (e[6], e[7], e[8])  # stored, real, off
    return ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versions', default='GR_ZH98,GR_ZH101,GR_ZH105,GR_ZH109,GR_ZH111,GR_ZH113,GR_ZH114,GR_ZH115')
    ap.add_argument('--control', default='GR_EN_ORIG')
    a = ap.parse_args()

    def iso(v):
        return os.path.join(BUILDS, v, '%s.iso' % v)

    ref = {k: iso_entries(iso(a.control), lba) for k, lba in IMGS.items()}
    print('控制盘 %s: MENU %d 条目 / GR %d 条目' %
          (a.control, len(ref['MENU.IMG']), len(ref['GR.IMG'])))

    vers = [v.strip() for v in a.versions.split(',') if v.strip()]
    for v in vers:
        p = iso(v)
        if not os.path.isfile(p):
            print('%-10s (缺 ISO)' % v)
            continue
        line = []
        for k, lba in IMGS.items():
            try:
                cur = iso_entries(p, lba)
            except Exception as ex:
                line.append('%s ERR %s' % (k, ex))
                continue
            moved = []
            for nm, (st, rl, off) in cur.items():
                r = ref[k].get(nm)
                if r is None:
                    moved.append((nm, 'NEW'))
                elif (st, rl, off) != r:
                    moved.append((nm, 'off %d->%d' % (r[2], off)))
            line.append('%s: 条目 %d, 与原盘不同 %d %s' %
                        (k, len(cur), len(moved), moved[:4] if moved else ''))
        print('%-10s %s' % (v, ' | '.join(line)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
