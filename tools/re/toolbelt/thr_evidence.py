# -*- coding: utf-8 -*-
r"""thr_evidence.py -- round86 证据表: 每张盘的 (stored, real, 记录链长, 读流落点) 对照

用法: python tools/re/toolbelt/thr_evidence.py
"""
import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

SEC = 2048
MENU_LBA = tcslib.MENU_LBA
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def read_stop(log):
    fr = {}
    n = 0
    with open(log, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            a = line.strip().split()
            if len(a) < 2:
                continue
            n += 1
            fr.setdefault(int(a[0]), []).append(int(a[1]))
    if not fr:
        return None
    last = max(fr)
    return dict(events=n, last_frame=last, frames=len(fr), maxlba=max(x for v in fr.values() for x in v),
                lastlba=max(fr[last]))


ROWS = [
    ('GR_ZH124 (基底, 可用)', r'work\builds\GR_ZH124\GR_ZH124.iso',
     r'work\builds\GR_THR86\temp\dump_base\cdvd.log'),
    ('h640_skipreal (只改 stored)', r'work\builds\GR_THR86\GR_THR86_h640_skipreal.iso',
     r'work\builds\GR_THR86\temp\dump_h640_skip\cdvd.log'),
    ('h640 v2 (stored+real 同步)', r'work\builds\GR_THR86\v2_h640.iso',
     r'work\builds\GR_THR86\temp\dump_v2_h640\cdvd.log'),
    ('h513 skipreal (只改 stored)', r'work\builds\GR_THR86\GR_THR86_h513.iso',
     r'work\builds\GR_THR86\temp\dump_h513\cdvd.log'),
    ('h513 v2 (stored+real 同步)', r'work\builds\GR_THR86\v2_h513.iso',
     r'work\builds\GR_THR86\temp\dump_v2_h513\cdvd.log'),
    ('h512 旧px_size规则(+384)', r'work\builds\GR_THR86\GR_THR86_h512.iso',
     r'work\builds\GR_THR86\temp\dump_h512\cdvd.log'),
    ('w2048 v2 (stored+real 同步)', r'work\builds\GR_THR86\v2_w2048.iso',
     r'work\builds\GR_THR86\temp\dump_v2_w2048\cdvd.log'),
    ('W2048 老探针(ROOT85_gate)', r'work\builds\GR_ROOT85\GR_ROOT85_gate.iso',
     r'work\builds\GR_ROOT85\temp\dump_gate\cdvd.log'),
]


def main():
    print('=' * 132)
    print('%-28s %10s %10s %11s %11s %9s %9s %9s %5s' %
          ('盘', 'stored', 'real', 'min(st,re)', '链长', 'stopLBA', 'PAK+字节', 'maxLBA', 'PNG'))
    print('-' * 132)
    for (label, iso_p, log_p) in ROWS:
        iso_abs = os.path.join(REPO, iso_p)
        log_abs = os.path.join(REPO, log_p)
        if not os.path.isfile(iso_abs):
            print('%-28s (缺 ISO)' % label)
            continue
        iso = tcslib.Iso(iso_abs)
        ents = zx_lib.entries(iso, MENU_LBA)
        e = [x for x in ents if x['name'] == 'COMMON.PAK'][0]
        pak = bytes(iso.read(e['iso_off'], e['stored']))
        recs = tcslib.parse_pak_records(pak)
        chain = recs[-1][6] + recs[-1][5]        # 末条记录 end
        # 记录链哨兵后 4 B
        chain += 4
        cx, ch = recs[1][2], recs[1][3]
        iso.close()
        rs = read_stop(log_abs) if os.path.isfile(log_abs) else None
        png = len(glob.glob(os.path.join(os.path.dirname(log_abs), 'snap_*.png')))
        if rs:
            pb = (rs['lastlba'] - MENU_LBA) * SEC + SEC - e['off']
            print('%-28s %10d %10d %11d %11d %9d %9d %9d %5d   %dx%d' %
                  (label, e['stored'], e['real'], min(e['stored'], e['real']), chain,
                   rs['lastlba'], pb, rs['maxlba'], png, cx, ch))
        else:
            print('%-28s %10d %10d %11d %11d   (无 cdvd.log)' %
                  (label, e['stored'], e['real'], min(e['stored'], e['real']), chain))
    print('-' * 132)
    print('注: "PAK+字节" = 最后一次读到的那一扇区末尾相对 PAK 起点的字节偏移（上取整到扇区）。')
    print('    real 未更新的盘（stored>real）PAK+字节 ≈ 400,659..429,056 ⇒ 与 real 的旧值 400,659 同扇区簇。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
