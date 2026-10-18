# -*- coding: utf-8 -*-
r"""thr_run_seq.py -- 串行跑多张盘 (gsrunner 单实例独占), 每张 6000 帧 + nav 输入。

    python tools/re/toolbelt/thr_run_seq.py --dump-root work\builds\GR_THR86\temp ^
        --iso work\builds\GR_THR86\GR_THR86_h640.iso:dump_h640 ^
        --iso work\builds\GR_THR86\GR_THR86_w2048.iso:dump_w2048
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump-root', required=True)
    ap.add_argument('--iso', action='append', required=True, help='<iso>:<subdir>')
    ap.add_argument('--nav', default=r'tools\capture\nav_menu_only.txt')
    ap.add_argument('--maxframes', default='6000')
    ap.add_argument('--snap', default='30')
    a = ap.parse_args()
    root = os.path.abspath(a.dump_root)
    os.makedirs(root, exist_ok=True)
    for spec in a.iso:
        p, sub = spec.rsplit(':', 1)
        dump = os.path.join(root, sub)
        cmd = [sys.executable, os.path.join(HERE, 'root_run.py'),
               '--iso', p, '--dump', dump, '--maxframes', a.maxframes,
               '--snap', a.snap, '--nav', a.nav,
               '--log', os.path.join(root, 'stdout_%s.txt' % sub)]
        print('[seq] >>> %s' % ' '.join(cmd), flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        print(r.stdout, flush=True)
        if r.stderr:
            print('[stderr] %s' % r.stderr, flush=True)
        print('[seq] <<< exit=%d elapsed=%.0fs %s' % (r.returncode, time.time() - t0, p),
              flush=True)
    print('[seq] ALL DONE', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
