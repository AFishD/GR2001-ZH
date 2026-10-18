# -*- coding: utf-8 -*-
r"""rb_dumpcover.py -- 只读：统计 PCSX2 cdvd-dump 的扇区并集覆盖，以及它与
「EN 原盘 vs 汉化盘」差异区间的交叠（回答：能否用 dump 取回汉化盘的被改字节）。

用法: python rb_dumpcover.py [--json <evidence_diff_en_vs_zh113b.json>] [--out <txt>]
"""
import argparse
import glob
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
            raise SystemExit('not BDV2: %s' % path)
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            raise SystemExit('len check fail: %s rem=%d' % (path, rem))
        idx = {}
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            lba = struct.unpack('<I', f.read(4))[0]
            idx[lba] = 16 + i * (4 + SEC) + 4
    return idx, total, n


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=os.path.join(
        'work', 'builds', 'GR_CVAR', 'evidence_diff_en_vs_zh113b.json'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    dumps = sorted(glob.glob(os.path.join(DUMPDIR, '*.dump')))
    P('dump 目录 = %s ; 共 %d 个' % (DUMPDIR, len(dumps)))
    allidx = {}
    per = []
    total_lba = None
    for d in dumps:
        try:
            idx, total, n = load_idx(d)
        except SystemExit as e:
            P('[skip] %s (%s)' % (os.path.basename(d), e))
            continue
        total_lba = total
        per.append((os.path.basename(d), len(idx), min(idx), max(idx)))
        for k in idx:
            allidx.setdefault(k, []).append(os.path.basename(d))
    P('')
    P('%-46s %8s %10s %10s' % ('dump', 'sectors', 'lba_min', 'lba_max'))
    for nm, c, lo, hi in per:
        P('%-46s %8d %10d %10d' % (nm, c, lo, hi))
    P('')
    P('[union] total_lba=%d ; 并集扇区 = %d (%.2f%%)' % (total_lba, len(allidx),
                                                        100.0 * len(allidx) / total_lba))

    # 多 dump 覆盖的
    multi = sum(1 for v in allidx.values() if len(v) > 1)
    P('[union] 被 >=2 个 dump 覆盖的扇区 = %d' % multi)

    # ── 与差异区间的交叠 ──
    if os.path.exists(a.json):
        d = json.load(open(a.json, encoding='utf-8'))
        coarse = [tuple(x) for x in d['coarse']]
        runs = [tuple(x) for x in d['runs']]
        P('')
        P('差异证据 = %s  (a=%s b=%s)' % (a.json, d['a'], d['b']))
        P('coarse 区间 %d 个 ; runs(逐段) %d 个' % (len(coarse), len(runs)))
        cov_all = 0
        miss_all = 0
        P('')
        P('%-4s %-14s %-14s %10s %10s %10s %8s' %
          ('#', 'off_start', 'off_end', 'bytes', 'cov_sect', 'miss_sect', 'cov%'))
        detail = []
        for i, (s, e) in enumerate(coarse, 1):
            l0, l1 = s // SEC, (e - 1) // SEC
            n = l1 - l0 + 1
            have = sum(1 for l in range(l0, l1 + 1) if l in allidx)
            miss = n - have
            cov_all += have
            miss_all += miss
            P('%-4d %-14d %-14d %10d %10d %10d %7.1f%%' %
              (i, s, e, e - s, have, miss, 100.0 * have / n))
            detail.append(dict(i=i, off0=s, off1=e, lba0=l0, lba1=l1,
                               n=n, have=have, miss=miss,
                               miss_lbas=[l for l in range(l0, l1 + 1) if l not in allidx][:40]))
        P('')
        P('[coarse] 扇区合计 %d ; 覆盖 %d (%.1f%%) ; 缺 %d' %
          (cov_all + miss_all, cov_all, 100.0 * cov_all / (cov_all + miss_all), miss_all))
        # 保守口径：只按 runs(逐字节差异段) 算
        rl = set()
        for (s, e) in runs:
            for l in range(s // SEC, (e - 1) // SEC + 1):
                rl.add(l)
        have_r = sum(1 for l in rl if l in allidx)
        P('[runs  ] 涉及扇区 %d ; 覆盖 %d (%.1f%%) ; 缺 %d' %
          (len(rl), have_r, 100.0 * have_r / len(rl), len(rl) - have_r))
        out = a.out or os.path.join('work', 'builds', 'GR_REBUILD', 'temp',
                                    'dumpcover.txt')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(dict(union=len(allidx), total_lba=total_lba, per=per,
                       coarse_miss_lbas=detail,
                       coarse_have=cov_all, coarse_miss=miss_all,
                       runs_lbas=len(rl), runs_have=have_r),
                  open(out + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    out = a.out or os.path.join('work', 'builds', 'GR_REBUILD', 'temp', 'dumpcover.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
