# -*- coding: utf-8 -*-
r"""root_run.py -- round85 实机跑（gsrunner 串行, 单实例）。用法见 --help。

  python tools/re/toolbelt/root_run.py --iso <iso> --dump <dir> [--maxframes 6000] [--snap 500]
                                [--nav tools\capture\nav_xxx.txt] [--memwatch ...]
不传 --nav 时用 -grinputlive（脚本时间线）—— 需要 --live 文件。
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
    ap.add_argument('--live', default=None)
    ap.add_argument('--maxframes', default='6000')
    ap.add_argument('--snap', default='500')
    ap.add_argument('--scanframes', default='4000')
    ap.add_argument('--renderer', default='dx11')
    ap.add_argument('--log', default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    iso = os.path.abspath(a.iso).replace('/', '\\')
    dump = os.path.abspath(a.dump).replace('/', '\\')
    assert os.path.isfile(iso), '没这个 ISO: %s' % iso
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
            '-grsnap', a.snap, '-grmaxframes', a.maxframes,
            '-grmemcards', mcd]
    if a.nav:
        nav = os.path.abspath(a.nav).replace('/', '\\')
        args += ['-grinput', nav]
    if a.live:
        args += ['-grinputlive', os.path.abspath(a.live).replace('/', '\\')]
    args += ['-renderer', a.renderer, '--', iso]
    print('[root_run] %s' % ' '.join(args))
    t0 = time.time()
    logp = a.log or os.path.join(dump, '..', 'root_run_stdout.txt')
    with open(logp, 'wb') as fh:
        r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=fh, stderr=subprocess.STDOUT)
    print('[root_run] exit=%d elapsed=%.0fs dump=%s' % (r.returncode, time.time() - t0, dump))
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
