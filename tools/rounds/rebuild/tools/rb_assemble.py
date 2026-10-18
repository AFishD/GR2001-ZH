# -*- coding: utf-8 -*-
r"""rb_assemble.py -- 用「基底 ISO + PCSX2 块转储扇区」拼出一张盘（只写 work/builds/GR_REBUILD/**）。

原理：BDV2 转储里存的是**当次实跑读到的原始扇区**（2048 B 粒度，带 LBA）。
按优先级顺序把各转储的扇区覆盖到基底 ISO 上，即得到"该盘 + 未覆盖区仍为基底"的混合盘。

用法:
  python rb_assemble.py --out <iso> [--dumps "名1,名2"] [--report <json>] [--base <iso>]
"""
import argparse
import glob
import io
import json
import os
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
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
        hdr = f.read(16)
        magic, bsz, total, zero = struct.unpack('<4sIII', hdr)
        if magic != b'BDV2' or bsz != SEC:
            return None, None, n
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            return None, None, n
        idx = {}
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            lba = struct.unpack('<I', f.read(4))[0]
            idx[lba] = 16 + i * (4 + SEC) + 4
    return idx, total, n


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--base', default=os.path.join(
        REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso"))
    ap.add_argument('--dumps', default='')
    ap.add_argument('--order', default='')       # 逗号分隔的优先级顺序（先者优先）
    ap.add_argument('--report', default=None)
    ap.add_argument('--no-write', action='store_true')
    a = ap.parse_args(argv)

    all_dumps = sorted(glob.glob(os.path.join(DUMPDIR, '*.dump')))
    if a.order:
        want = [x.strip() for x in a.order.split(',') if x.strip()]
        picked = []
        for w in want:
            hit = [d for d in all_dumps if w in os.path.basename(d) and d not in picked]
            if not hit:
                raise SystemExit('转储未找到: %s' % w)
            picked.append(hit[0])
    else:
        picked = all_dumps
    P('基底 = %s (%d B)' % (a.base, os.path.getsize(a.base)))
    P('转储优先级（先者胜）=')
    loaded = []
    for d in picked:
        idx, total, n = load_idx(d)
        if idx is None:
            P('   [跳过] %-52s 不可读/长度自检失败' % os.path.basename(d))
            continue
        loaded.append((os.path.basename(d), idx))
        P('   %-52s %6d 扇区' % (os.path.basename(d), len(idx)))

    # 逐扇区覆盖统计
    owner = {}                       # lba -> dump name
    for nm, idx in loaded:
        for lba in idx:
            if lba not in owner:
                owner[lba] = nm
    P('')
    P('[覆盖] 命中扇区 %d ; 由各转储提供:' % len(owner))
    from collections import Counter
    c = Counter(owner.values())
    for nm, k in c.most_common():
        P('   %-52s %6d 扇区 (%.2f MB)' % (nm, k, k * SEC / 1048576.0))

    base_size = os.path.getsize(a.base)
    nsec = base_size // SEC
    if base_size % SEC:
        raise SystemExit('基底不是 2048 的整数倍')
    P('[基底] %d 扇区 (%d B)' % (nsec, base_size))

    if not a.no_write:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        if os.path.exists(a.out):
            raise SystemExit('输出已存在，拒绝覆盖: %s' % a.out)
        tmp = a.out + '.part'
        with open(a.base, 'rb') as fi, open(tmp, 'wb') as fo:
            # 先整份拷贝基底，再逐转储按优先级改写命中的扇区（后写的必须让位）
            shutil.copyfileobj(fi, fo, 8 << 20)
            fo.flush()
        # 按优先级从低到高覆盖（高优先级最后写）
        with open(tmp, 'r+b') as fo:
            for nm, idx in reversed(loaded):
                buf = {}
                with open(os.path.join(DUMPDIR, [d for d in picked
                                                 if os.path.basename(d) == nm][0]), 'rb') as fd:
                    for lba, off in sorted(idx.items()):
                        if lba >= nsec:
                            continue
                        fd.seek(off)
                        fo.seek(lba * SEC)
                        fo.write(fd.read(SEC))
        os.replace(tmp, a.out)
        P('[out] %s  %d B' % (a.out, os.path.getsize(a.out)))

    rep = dict(base=a.base, out=a.out, nsec=nsec, covered=len(owner),
               per_dump={k: v for k, v in c.items()},
               owner_map=os.path.join(os.path.dirname(os.path.abspath(
                   a.report or a.out)), 'owner_map.json'))
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        json.dump(rep, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # 落一份 owner 映射（按段压缩），供后续取证
        ks = sorted(owner)
        runs = []
        if ks:
            s = p = ks[0]
            for x in ks[1:]:
                if x == p + 1 and owner[x] == owner[p]:
                    p = x
                else:
                    runs.append([s, p, owner[s]])
                    s = p = x
            runs.append([s, p, owner[s]])
        json.dump(runs, open(rep['owner_map'], 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=0)
        P('[report] %s ; owner runs = %d' % (a.report, len(runs)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
