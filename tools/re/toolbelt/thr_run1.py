# -*- coding: utf-8 -*-
r"""thr_run1.py -- 单次 gsrunner 跑 (任意附加 -gr* 旗标), 串行独占

    python tools/re/toolbelt/thr_run1.py --iso <iso> --dump <dir> [--extra "-grpcsample 1"] ...
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--dump', required=True)
    ap.add_argument('--nav', default=None)
    ap.add_argument('--maxframes', default='6000')
    ap.add_argument('--snap', default='30')
    ap.add_argument('--scanframes', default='4000')
    ap.add_argument('--renderer', default='dx11')
    ap.add_argument('--extra', action='append', default=[])
    ap.add_argument('--log', default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    iso = os.path.abspath(a.iso).replace('/', '\\')
    dump = os.path.abspath(a.dump).replace('/', '\\')
    assert os.path.isfile(iso), iso
    mcd = os.path.join(os.path.dirname(dump), 'mc')
    os.makedirs(mcd, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        src = os.path.join(MC, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(mcd, f))
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    args = [GS, '-grdumpdir', dump, '-grscanframes', a.scanframes,
            '-grsnap', a.snap, '-grmaxframes', a.maxframes, '-grmemcards', mcd]
    if a.nav:
        args += ['-grinput', os.path.abspath(a.nav).replace('/', '\\')]
    for e in a.extra:
        args += e.split()
    args += ['-renderer', a.renderer, '--', iso]
    print('[run1] %s' % ' '.join(args), flush=True)
    t0 = time.time()
    logp = a.log or os.path.join(os.path.dirname(dump), 'run1_stdout.txt')
    with open(logp, 'wb') as fh:
        r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=fh, stderr=subprocess.STDOUT)
    print('[run1] exit=%d elapsed=%.0fs dump=%s' % (r.returncode, time.time() - t0, dump))
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
