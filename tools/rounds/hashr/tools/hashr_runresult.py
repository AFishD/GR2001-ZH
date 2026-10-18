# -*- coding: utf-8 -*-
r"""hashr_runresult.py — 解析一次 gsrunner 跑法的读数 (判据 5)

    python work/builds/GR_HASHR/tools/hashr_runresult.py --dump <dir> [--tag <name>]

判据: ≥190 截图 / `TLB Miss` 0 / 无 `Trap exception` / 到中文主菜单。
"到中文主菜单"的可判定代理: 与**同一命令跑出来的对照盘**逐帧比对
(本修复不改版式 ⇒ 画面应逐像素一致; 关键帧文件名与既有报告同口径)。
"""
import argparse
import collections
import glob
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SNAP_RE = re.compile(r'^snap_f(\d+)\.png$')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', required=True)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    d = os.path.abspath(a.dump)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.png')))
    frames = {}
    for p in snaps:
        m = SNAP_RE.match(os.path.basename(p))
        if m:
            frames[int(m.group(1))] = p
    log = os.path.join(d, 'emulog.txt')
    txt = ''
    if os.path.isfile(log):
        txt = io.open(log, encoding='utf-8', errors='replace').read()
    tlb = txt.count('TLB Miss')
    trap = len(re.findall(r'Trap exception', txt))
    tlb_lines = [l for l in txt.splitlines() if 'TLB Miss' in l]
    trap_lines = [l for l in txt.splitlines() if 'Trap exception' in l][:5]
    pc = collections.Counter(re.findall(r'pc=0x([0-9a-fA-F]+)', txt))
    run = io.open(os.path.join(d, 'RUN.txt'), encoding='utf-8',
                  errors='replace').read() if os.path.isfile(
        os.path.join(d, 'RUN.txt')) else ''
    other = sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, '*'))
                   if os.path.basename(p) not in ('mc',) and not p.endswith('.png'))
    res = dict(tag=a.tag or os.path.basename(d), dump=d, n_snap=len(snaps),
               first_frame=min(frames) if frames else None,
               last_frame=max(frames) if frames else None,
               unique_snap_sha=len({sha256_file(p) for p in snaps}),
               tlb_miss=tlb, trap_exception=trap, tlb_lines=tlb_lines[:5],
               trap_lines=trap_lines, pc_top=pc.most_common(12),
               files=other, run=run.strip().splitlines(),
               snap_sha={str(k): sha256_file(v) for k, v in sorted(frames.items())})
    print('=' * 90)
    print('%s  截图 %d 张 (帧 %s..%s) ; 去重 %d ; TLB Miss %d ; Trap exception %d'
          % (res['tag'], res['n_snap'], res['first_frame'], res['last_frame'],
             res['unique_snap_sha'], tlb, trap))
    print('  TLB 行: %s' % (tlb_lines[:3] or '无'))
    print('  停顿 PC top: %s' % (pc.most_common(6) or '无'))
    print('  目录文件: %s' % ', '.join(other))
    for l in res['run']:
        print('  RUN: %s' % l)
    ok = (res['n_snap'] >= 190 and tlb == 0 and trap == 0)
    res['criteria_ok'] = ok
    print('  ⇒ 判据 (≥190 截图 / TLB 0 / 无 Trap): %s' % ('✅ 通过' if ok else '✗ 未过'))
    out = a.json or os.path.join(d, 'result.json')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('  → %s' % out)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
