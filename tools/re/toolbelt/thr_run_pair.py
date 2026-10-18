# -*- coding: utf-8 -*-
r"""thr_run_pair.py -- 串行跑「对照 + 探针」(gsrunner 单实例独占)

    python tools/re/toolbelt/thr_run_pair.py --a <iso> --da <dumpdir> --b <iso> --db <dumpdir>
                                      [--maxframes 6000] [--snap 30]
先跑 A, 跑完确认进程退出, 再跑 B。
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run(iso, dump, nav, maxframes, snap, log):
    cmd = [sys.executable, os.path.join(HERE, 'root_run.py'),
           '--iso', iso, '--dump', dump, '--maxframes', str(maxframes),
           '--snap', str(snap), '--log', log]
    if nav:
        cmd += ['--nav', nav]
    print('[pair] >>> %s' % ' '.join(cmd), flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    print(r.stdout)
    if r.stderr:
        print('[stderr] %s' % r.stderr)
    print('[pair] <<< exit=%d elapsed=%.0fs (%s)' % (r.returncode, time.time() - t0, iso),
          flush=True)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--da', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--db', required=True)
    ap.add_argument('--nav', default=r'tools\capture\nav_menu_only.txt')
    ap.add_argument('--maxframes', default='6000')
    ap.add_argument('--snap', default='30')
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.da))
    os.makedirs(base, exist_ok=True)
    ra = run(a.a, a.da, a.nav, a.maxframes, a.snap, os.path.join(base, 'stdout_A.txt'))
    rb = run(a.b, a.db, a.nav, a.maxframes, a.snap, os.path.join(base, 'stdout_B.txt'))
    print('[pair] DONE ra=%d rb=%d' % (ra, rb), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
