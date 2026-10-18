# -*- coding: utf-8 -*-
r"""oomfix_frames.py —— 两次冷启动 6000 帧冒烟的**逐帧 sha256 对照** + 冒烟判据汇总。

用法:
  python oomfix_frames.py <dirA> <dirB> [--json out.json] [--pixel]
  python oomfix_frames.py <dir> --single          # 只汇总单次（截图数/TLB/Trap/帧区间）
"""
import argparse
import hashlib
import json
import os
import re
import sys

SNAP_RE = re.compile(r'^snap_f(\d+)\.png$')


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(d):
    snaps, shas = {}, {}
    for n in sorted(os.listdir(d)):
        m = SNAP_RE.match(n)
        if m:
            fr = int(m.group(1))
            snaps[fr] = os.path.join(d, n)
            shas[fr] = sha_file(snaps[fr])
    el = os.path.join(d, 'emulog.txt')
    tlb = trap = op = 0
    pausing = 0
    run_end = None
    if os.path.exists(el):
        with open(el, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if 'TLB Miss' in line:
                    tlb += 1
                elif 'Trap exception' in line:
                    trap += 1
                elif 'Unrecognized op' in line:
                    op += 1
                elif 'Pausing' in line:
                    pausing += 1
                elif '=== run end' in line:
                    run_end = line.strip()
    return dict(dir=os.path.abspath(d), snaps=snaps, shas=shas, n_snap=len(snaps),
                first=min(snaps) if snaps else None, last=max(snaps) if snaps else None,
                unique=len(set(shas.values())), tlb=tlb, trap=trap, op=op,
                pausing=pausing, run_end=run_end,
                emulog_bytes=os.path.getsize(el) if os.path.exists(el) else 0,
                ram5970=os.path.exists(os.path.join(d, 'win_f00005970_eeram.bin')))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b', nargs='?')
    ap.add_argument('--json', default=None)
    ap.add_argument('--pixel', action='store_true')
    ap.add_argument('--single', action='store_true')
    args = ap.parse_args()

    A = load(args.a)
    for tag, r in (('A', A),):
        print('%s = %s : 截图 %d（去重 %d）/ 帧 %s..%s / TLB %d / Trap %d / op %d / Pausing %d'
              % (tag, r['dir'], r['n_snap'], r['unique'], r['first'], r['last'],
                 r['tlb'], r['trap'], r['op'], r['pausing']))
        print('    %s' % r['run_end'])
    rep = dict(A=A)
    if args.b and not args.single:
        B = load(args.b)
        rep['B'] = B
        print('B = %s : 截图 %d（去重 %d）/ 帧 %s..%s / TLB %d / Trap %d / op %d / Pausing %d'
              % (B['dir'], B['n_snap'], B['unique'], B['first'], B['last'],
                 B['tlb'], B['trap'], B['op'], B['pausing']))
        print('    %s' % B['run_end'])
        common = sorted(set(A['shas']) & set(B['shas']))
        same = [f for f in common if A['shas'][f] == B['shas'][f]]
        diff = [f for f in common if A['shas'][f] != B['shas'][f]]
        rep.update(common=len(common), same=len(same), diff=len(diff),
                   diff_frames=['snap_f%08d.png' % f for f in diff])
        print('共同帧 %d；逐帧 sha256 **相同 %d** / **不同 %d**' % (len(common), len(same), len(diff)))
        print('不同帧: %s' % (rep['diff_frames'] if diff else '[] ⇒ 逐像素 0 差异'))
        if args.pixel and diff:
            try:
                from PIL import Image, ImageChops
                px = []
                for f in diff:
                    i1 = Image.open(A['snaps'][f]).convert('RGBA')
                    i2 = Image.open(B['snaps'][f]).convert('RGBA')
                    df = ImageChops.difference(i1, i2)
                    bb = df.getbbox()
                    n = 0 if bb is None else sum(1 for p in df.getdata() if p != (0, 0, 0, 0))
                    px.append(dict(frame=f, diff_px=n, bbox=bb))
                rep['pixel'] = px
                print('[pixel] %s' % ', '.join('%s:%s px %s'
                                               % (x['frame'][5:13], x['diff_px'], x['bbox'])
                                               for x in px))
            except Exception as e:                                            # noqa: BLE001
                print('[pixel] 不可用: %s' % e)
    if args.json:
        json.dump(rep, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[json] %s' % args.json)


if __name__ == '__main__':
    main()
