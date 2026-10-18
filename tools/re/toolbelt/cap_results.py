# -*- coding: utf-8 -*-
r"""cap_results.py -- Step 4 判据汇总 (exit=0 **不作判据**)

    python tools/re/toolbelt/cap_results.py <dumpdir> [<dumpdir2> ...]

每张盘给出:
  · 截图张数 / **sha256 去重后的画面数** (只看张数会被"卡死但照常出图"骗)
  · `TLB Miss` 行数 (**必须 0**) ; `Trap exception` 行数 (**必须 0**)
  · needle: newfontrevisedrs / new_font_revised / weaponsanditems
  · cdvd.log 读流: 事件数 / frame 跨度 / maxLBA
  · 与对照 dump 逐张同名 PNG 的 sha256 相同数 (画面一致性)
"""
import collections
import glob
import hashlib
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
    P('=' * 92)
    P('dump = %s' % d)
    if not os.path.isdir(d):
        P('[!!] 目录不存在')
        return None
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.png')))
    hs = collections.OrderedDict()
    for p in snaps:
        hs.setdefault(sha(p), []).append(os.path.basename(p))
    P('[png ] 截图 **%d** 张 ; sha256 去重后 **画面数 = %d**' % (len(snaps), len(hs)))
    if snaps:
        frames = sorted(int(re.search(r'snap_f?(\d+)', os.path.basename(p)).group(1)) for p in snaps)
        P('[png ] 帧号范围 %d..%d' % (frames[0], frames[-1]))
        P('[png ] 首帧 %s ; 末帧 %s' % (os.path.basename(snaps[0]), os.path.basename(snaps[-1])))
    top = sorted(hs.items(), key=lambda kv: -len(kv[1]))[:3]
    for h, fs in top:
        P('       %s × %-4d %s..%s' % (h[:12], len(fs), fs[0], fs[-1]))
    res = dict(dir=d, n_png=len(snaps), n_scene=len(hs), scenes=hs)
    for name in ('emulog.txt', 'stdout.txt', 'grlog.txt'):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            P('[log ] %-12s 不存在' % name)
            continue
        t = io.open(p, encoding='utf-8', errors='replace').read()
        P('[log ] %-12s %d 行 / %d B' % (name, t.count('\n'), len(t)))
        for nd in ('newfontrevisedrs', 'new_font_revised', 'weaponsanditems'):
            res['needle_' + nd] = len(re.findall(re.escape(nd), t))
            P('       needle %-20s **%d**' % (nd, res['needle_' + nd]))
        res['tlb_miss'] = len(re.findall(r'TLB Miss', t))
        res['trap'] = len(re.findall(r'Trap exception', t))
        res['tlb_any'] = len(re.findall(r'TLB', t))
        P('       ★ `TLB Miss` **%d** (全部 TLB 字样 %d) ; ★ `Trap exception` **%d**'
          % (res['tlb_miss'], res['tlb_any'], res['trap']))
        for pat in (r'TLB Miss.{0,80}', r'Trap exception.{0,80}'):
            for m in re.findall(pat, t)[:3]:
                P('       ! %s' % m.strip())
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
        res.update(ev=ev, f_lo=min(frames) if frames else -1,
                   f_hi=max(frames) if frames else -1, maxlba=max(lbas) if lbas else -1)
    else:
        P('[cdvd] 没有 cdvd.log')
    res['snap_files'] = snaps
    return res


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit(__doc__)
    info = [scan(d) for d in dirs]
    info = [i for i in info if i]
    if len(info) >= 2:
        base = info[-1]
        for i in info[:-1]:
            P('=' * 92)
            fa = {os.path.basename(p): p for p in i['snap_files']}
            fb = {os.path.basename(p): p for p in base['snap_files']}
            common = sorted(set(fa) & set(fb))
            same = sum(1 for n in common if sha(fa[n]) == sha(fb[n]))
            P('[cmp] %s vs **对照** %s : 同名可比 %d 张 ; 逐字节相同 **%d** (%.1f%%)'
              % (os.path.basename(i['dir']), os.path.basename(base['dir']), len(common), same,
                 100.0 * same / max(1, len(common))))
            diff = [n for n in common if sha(fa[n]) != sha(fb[n])]
            P('[cmp] 不同 %d 张 %s' % (len(diff), diff[:10]))
            if len(i['snap_files']) != len(base['snap_files']):
                P('[cmp] ★ 张数不同: %d vs %d' % (len(i['snap_files']), len(base['snap_files'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
