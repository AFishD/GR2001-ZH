# -*- coding: utf-8 -*-
r"""run_r45.py — round45 实机跑带 (runcap.py 的可控版: 转储目录/参数全显式)

用法:
  python tools/capture/run_r45.py --iso <iso> --nav <nav.txt> --dump <转储目录> \
         [--maxframes 31000] [--snap 100] [--scanframes 4000] [--renderer dx11]

说明:
  · gsrunner 以自身目录为 cwd ⇒ --iso / --dump / --nav 一律转成绝对路径;
  · ISO 路径必须用反斜杠 (正斜杠会秒退, 见 docs/PROGRESS.md);
  · 记忆卡从 third_party/emu/run/memcards 复制到 **转储目录的兄弟目录 mc/**;
  · 每次只跑一个实例 (实机串行, 不并发)。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--nav', required=True)
    ap.add_argument('--dump', required=True)
    ap.add_argument('--maxframes', default='31000')
    ap.add_argument('--snap', default='100')
    ap.add_argument('--scanframes', default='4000')
    ap.add_argument('--renderer', default='dx11')
    ap.add_argument('--log', default=None, help='把 gsrunner 的 stdout/stderr 写到这里')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    iso = os.path.abspath(a.iso).replace('/', '\\')
    nav = os.path.abspath(a.nav).replace('/', '\\')
    dump = os.path.abspath(a.dump).replace('/', '\\')
    assert os.path.isfile(iso), '没这个 ISO: %s' % iso
    assert os.path.isfile(nav), '没这个 nav: %s' % nav
    mcd = os.path.join(os.path.dirname(dump), 'mc')
    os.makedirs(mcd, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(mcd, f))
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    args = [GS, '-grdumpdir', dump, '-grscanframes', a.scanframes,
            '-grsnap', a.snap, '-grmaxframes', a.maxframes,
            '-grmemcards', mcd, '-grinput', nav,
            '-renderer', a.renderer, '--', iso]
    print('[run_r45] iso=%s' % iso)
    print('[run_r45] nav=%s' % nav)
    print('[run_r45] dump=%s' % dump)
    print('[run_r45] frames=%s snap=%s' % (a.maxframes, a.snap))
    t0 = time.time()
    logp = a.log
    if logp:
        with open(logp, 'wb') as fh:
            r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=fh, stderr=subprocess.STDOUT)
    else:
        r = subprocess.run(args, cwd=os.path.dirname(GS))
    print('[run_r45] exit=%d elapsed=%.0fs dump=%s' % (r.returncode, time.time() - t0, dump))
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
