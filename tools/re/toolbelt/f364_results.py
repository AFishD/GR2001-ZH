# -*- coding: utf-8 -*-
r"""f364_results.py -- 实机判据汇总（exit=0 不作判据）

  · 截图张数 + **去重后的画面数**（sha256）
  · needle 行数: newfontrevisedrs / weaponsanditems / new_font_revised
  · TLB Miss 行数
  · cdvd.log 读流: 事件数 / frame 跨度 / maxLBA
  · 与对照盘逐张 PNG 逐字节比对
用法: python work\tools\f364_results.py [dumpdir ...]
"""
import collections
import glob
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_F364')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def scan(d):
    P('=' * 78)
    P('dump = %s' % d)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.png')))
    P('[png] 截图 **%d** 张' % len(snaps))
    hs = collections.OrderedDict()
    for p in snaps:
        hs.setdefault(sha(p), []).append(os.path.basename(p))
    P('[png] 去重后 **画面数 = %d**（同画面最多重复 %d 张: %s）'
      % (len(hs), max(len(v) for v in hs.values()),
         max(hs.values(), key=len)[:3]))
    top = sorted(hs.items(), key=lambda kv: -len(kv[1]))[:4]
    for h, fs in top:
        P('      %s × %d  %s..%s' % (h[:12], len(fs), fs[0], fs[-1]))

    for name in ('emulog.txt', 'grlog.txt', 'emulator.log'):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            P('[log] %-14s 不存在' % name)
            continue
        t = io.open(p, encoding='utf-8', errors='replace').read()
        P('[log] %-14s %d 行' % (name, t.count('\n')))
        for nd in ('newfontrevisedrs', 'weaponsanditems', 'new_font_revised',
                   'TLB Miss', 'TLB', 'GIFTAG'):
            n = len(re.findall(re.escape(nd), t))
            P('      needle %-22s **%d**' % (nd, n))

    p = os.path.join(d, 'cdvd.log')
    if os.path.exists(p):
        ev, lbas, frames = 0, [], []
        with io.open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                q = line.split()
                if len(q) != 2:
                    continue
                ev += 1
                try:
                    a, b = q
                    frames.append(int(a))
                    lbas.append(int(b))
                except ValueError:
                    continue
        P('[cdvd] 事件 %d ; frame %d..%d ; maxLBA **%d** ; 去重扇区 %d'
          % (ev, min(frames) if frames else -1, max(frames) if frames else -1,
             max(lbas) if lbas else -1, len(set(lbas))))
    else:
        P('[cdvd] 没有 cdvd.log')
    return snaps, hs


def main():
    dirs = sys.argv[1:] or [os.path.join(OUTDIR, 'temp', 'dump_f364'),
                            os.path.join(OUTDIR, 'temp', 'dump_ctl124')]
    info = [scan(d) for d in dirs]
    if len(info) >= 2:
        P('=' * 78)
        a, b = info[0][0], info[1][0]
        fa = {os.path.basename(p): p for p in a}
        fb = {os.path.basename(p): p for p in b}
        common = sorted(set(fa) & set(fb))
        P('[cmp] A=%s (%d 张) vs B=%s (%d 张) ; 同名可比 %d 张'
          % (os.path.basename(os.path.dirname(a[0])), len(fa),
             os.path.basename(os.path.dirname(b[0])), len(fb), len(common)))
        same, diffs = 0, []
        for n in common:
            if sha(fa[n]) == sha(fb[n]):
                same += 1
            else:
                diffs.append(n)
        P('[cmp] ★ 逐字节相同 **%d / %d** ; 不同 %d 张 %s'
          % (same, len(common), len(diffs), diffs[:12]))
        # 同名不同 = 真差异？再用像素比对
        try:
            from PIL import Image
            import numpy as np
            for n in diffs[:12]:
                ia = np.asarray(Image.open(fa[n]).convert('RGB')).astype(np.int16)
                ib = np.asarray(Image.open(fb[n]).convert('RGB')).astype(np.int16)
                dpx = int((np.abs(ia - ib).sum(axis=2) > 0).sum()) if ia.shape == ib.shape else -1
                P('      %s : 像素不同 %s / %d' % (n, dpx, ia.shape[0] * ia.shape[1]))
        except Exception as e:                                        # noqa: BLE001
            P('      (像素比对跳过: %s)' % e)
    with io.open(os.path.join(OUTDIR, 'f364_results.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
