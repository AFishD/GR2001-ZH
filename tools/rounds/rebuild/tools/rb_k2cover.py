# -*- coding: utf-8 -*-
r"""rb_k2cover.py -- 只读：K2 块转储对 GR.IMG / MENU.IMG 各区域的覆盖矩阵，
以及「K2 盘 ELF + K2 盘 MENU.IMG 扇区 + 原盘其余」这种拼装法能覆盖多少汉化差异面。

用法: python rb_k2cover.py [--dump <name-substr>] [--out <txt>]
"""
import argparse
import glob
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

SEC = 2048
DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def load_idx(path):
    n = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic, bsz, total, zero = struct.unpack('<4sIII', f.read(16))
        if magic != b'BDV2':
            return None, total
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            return None, total
        idx = set()
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            idx.add(struct.unpack('<I', f.read(4))[0])
    return idx, total


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', default='GR_FA2400_K2')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    dumps = sorted(glob.glob(os.path.join(DUMPDIR, '*.dump')))
    pick = [d for d in dumps if a.dump in os.path.basename(d)]
    P('目标 dump: %s' % [os.path.basename(x) for x in pick])
    k2, total = load_idx(pick[0])
    P('[k2 ] 扇区 %d ; total_lba %d' % (len(k2), total))
    ks = sorted(k2)
    runs = []
    s = p = ks[0]
    for x in ks[1:]:
        if x == p + 1:
            p = x
        else:
            runs.append((s, p))
            s = p = x
    runs.append((s, p))
    P('[k2 ] 连续段 %d 个:' % len(runs))
    for x, y in runs:
        P('     %7d..%-7d  %6d 扇区  %9d B  (iso 0x%X..0x%X)' %
          (x, y, y - x + 1, (y - x + 1) * SEC, x * SEC, (y + 1) * SEC))

    # 结构位置
    iso_orig = os.path.join(REPO, 'third_party', 'orig', 'ps2',
                            "Tom Clancy's Ghost Recon (USA).iso")
    iso = T.Iso(iso_orig)
    men = zx_lib.entries(iso, zx_lib.MENU_LBA)
    P('')
    P('[MENU.IMG] 条目 %d 个（只列被 K2 dump 部分/完全覆盖的）' % len(men))
    P('% -4s %-30s %-12s %-12s %10s %8s %8s' %
      ('idx', 'name', 'iso_off', 'iso_end', 'stored', 'lba0', 'lba1'))
    for e in men:
        l0, l1 = e['iso_off'] // SEC, (e['iso_off'] + e['stored'] - 1) // SEC
        have = sum(1 for l in range(l0, l1 + 1) if l in k2)
        if have:
            P('%-4d %-30s 0x%08X 0x%08X %10d %8d %8d  cov %d/%d (%.0f%%)' %
              (e['idx'], e['name'], e['iso_off'], e['iso_off'] + e['stored'],
               e['stored'], l0, l1, have, l1 - l0 + 1, 100.0 * have / (l1 - l0 + 1)))

    # GR.IMG 段覆盖
    gr_lba = zx_lib.GR_LBA
    gr_off = gr_lba * SEC
    gr_size = 1550563328
    gl0, gl1 = gr_off // SEC, (gr_off + gr_size - 1) // SEC
    have = sum(1 for l in range(gl0, gl1 + 1) if l in k2)
    P('')
    P('[GR.IMG] LBA %d..%d ; K2 dump 覆盖 %d / %d (%.2f%%) = %.2f MB' %
      (gl0, gl1, have, gl1 - gl0 + 1, 100.0 * have / (gl1 - gl0 + 1), have * SEC / 1048576.0))
    P('[GR.IMG] 被覆盖的连续段:')
    inr = [(x, y) for (x, y) in runs if x >= gl0 and y <= gl1]
    for x, y in inr:
        P('     lba %7d..%-7d (%6d 扇区, %8.2f MB)  = GR.IMG 内偏移 %d..%d' %
          (x, y, y - x + 1, (y - x + 1) * SEC / 1048576.0, x * SEC - gr_off,
           (y + 1) * SEC - gr_off))
    iso.close()

    # 与差异证据交叠
    j = os.path.join(REPO, 'work', 'builds', 'GR_CVAR', 'evidence_diff_en_vs_zh113b.json')
    d = json.load(open(j, encoding='utf-8'))
    coarse = [tuple(x) for x in d['coarse']]
    P('')
    P('EN-vs-ZH113b 差异区间 × K2 dump 覆盖:')
    P('%-4s %-14s %-14s %10s %8s %8s %10s' % ('#', 'off0', 'off1', 'bytes', 'sect', 'have', 'miss'))
    tot = tot_have = 0
    misslist = []
    for i, (s, e) in enumerate(coarse, 1):
        l0, l1 = s // SEC, (e - 1) // SEC
        n = l1 - l0 + 1
        h = sum(1 for l in range(l0, l1 + 1) if l in k2)
        tot += n
        tot_have += h
        P('%-4d %-14d %-14d %10d %8d %8d %10d' % (i, s, e, e - s, n, h, n - h))
        if n - h:
            misslist.append((i, s, e, [l for l in range(l0, l1 + 1) if l not in k2]))
    P('[合计] %d 扇区 ; K2 dump 覆盖 %d (%.1f%%) ; 缺 %d' %
      (tot, tot_have, 100.0 * tot_have / tot, tot - tot_have))
    P('')
    P('缺的连续块（每区间合并）:')
    for i, s, e, ml in misslist:
        ml = sorted(ml)
        rr = []
        st = p = ml[0]
        for x in ml[1:]:
            if x == p + 1:
                p = x
            else:
                rr.append((st, p))
                st = p = x
        rr.append((st, p))
        P('  区间 #%d (0x%X..0x%X): 缺 %d 扇区, %d 段: %s' %
          (i, s, e, len(ml), len(rr), ['%d..%d' % r for r in rr]))

    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'k2cover.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
