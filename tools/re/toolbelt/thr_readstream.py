# -*- coding: utf-8 -*-
r"""thr_readstream.py -- cdvd.log 读流解剖 (READ-ONLY)

cdvd.log 每行 = `<frame> <lba>`（每扇区一行）。本工具:
  · 按 frame 分组 → 连续 LBA 折成区间
  · 报告: 总行数 / 最后 frame / maxLBA / frame 跨度
  · 可把 LBA 映射成 MENU.IMG 内偏移与 COMMON.PAK 内偏移 (给 --iso)

用法:
  python tools/re/toolbelt/thr_readstream.py <cdvd.log> [--iso <iso>] [--f0 A] [--f1 B]
                                      [--tail N] [--all]
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..'), ))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

SEC = 2048
MENU_LBA = tcslib.MENU_LBA


def load(p):
    frames = {}
    n = 0
    with open(p, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            a = line.split()
            if len(a) < 2:
                continue
            fr, lba = int(a[0]), int(a[1])
            frames.setdefault(fr, []).append(lba)
            n += 1
    return frames, n


def ranges(v):
    v = sorted(v)
    out = []
    s = p = v[0]
    for x in v[1:]:
        if x == p + 1:
            p = x
            continue
        out.append((s, p))
        s = p = x
    out.append((s, p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--iso', default=None)
    ap.add_argument('--f0', type=int, default=None)
    ap.add_argument('--f1', type=int, default=None)
    ap.add_argument('--tail', type=int, default=12)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    frames, n = load(a.log)
    fl = sorted(frames)
    allb = [x for v in frames.values() for x in v]
    print('=' * 96)
    print('%s' % a.log)
    print('  行数(扇区事件)=%d ; frame 数=%d ; frame 跨度 %d..%d ; 唯一 LBA %d ; '
          'minLBA=%d maxLBA=%d' % (n, len(fl), fl[0], fl[-1], len(set(allb)), min(allb), max(allb)))

    # 映射表
    pak_off = ct_off = ct_len = w = h = None
    if a.iso:
        iso = tcslib.Iso(a.iso)
        ents = zx_lib.entries(iso, MENU_LBA)
        e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
        pak_off = e_pak['off']
        pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
        recs = tcslib.parse_pak_records(pak)
        w, h, ct_len, ct_off = recs[1][2], recs[1][3], recs[1][5], recs[1][6]
        print('  PAK  %d B @MENU+0x%X ; 容器 %d B (0x%X) @PAK+0x%X ; w=%d h=%d'
              % (e_pak['stored'], pak_off, ct_len, ct_len, ct_off, w, h))
        print('  FONT.RES off=0x%X' % [e['off'] for e in ents if e['name'] == 'FONT.RES'][0])
        iso.close()

    def dec(lba):
        b = (lba - MENU_LBA) * SEC                      # MENU.IMG 内字节偏移
        s = 'MENU+0x%X' % b if b >= 0 else '?'
        if pak_off is not None:
            pb = b - pak_off
            if ct_off is not None and ct_off <= pb < ct_off + ct_len:
                s += ' PAK%+d 容器[%d/%d]' % (pb, pb - ct_off, ct_len)
            elif pak_off <= pb:
                s += ' PAK+%d' % pb
            else:
                s += ' (PAK之前)'
        return s

    if a.f0 is not None or a.f1 is not None:
        lo = a.f0 if a.f0 is not None else fl[0]
        hi = a.f1 if a.f1 is not None else fl[-1]
        print('  --- frame %d..%d 逐帧区间 ---' % (lo, hi))
        for fr in range(lo, hi + 1):
            v = frames.get(fr)
            if not v:
                continue
            rr = ranges(v)
            print('    f%-6d %6d 扇区  %s' % (fr, len(v), ' '.join('%d..%d' % r for r in rr)))
            for (x, y) in rr:
                print('            LBA %d..%d  = %s .. %s' % (x, y, dec(x), dec(y)))

    if a.all:
        print('  --- 全部 frame ---')
        for fr in fl:
            rr = ranges(frames[fr])
            print('    f%-6d %6d 扇区  %s' % (fr, len(frames[fr]),
                                             ' '.join('%d..%d' % r for r in rr)))
    else:
        print('  --- 最后 %d 个有读盘的 frame ---' % a.tail)
        for fr in fl[-a.tail:]:
            rr = ranges(frames[fr])
            print('    f%-6d %6d 扇区  %s   [%s .. %s]'
                  % (fr, len(frames[fr]), ' '.join('%d..%d' % r for r in rr),
                     dec(min(frames[fr])), dec(max(frames[fr]))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
