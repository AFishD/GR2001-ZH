# -*- coding: utf-8 -*-
r"""fix_zh116_run.py — round70: 用即时存档跑 gsrunner (复现"存档后加载黑屏")

需要自定义 gsrunner 的 `-grstate <p2s>` (本轮新增; 官方 gsrunner 没有读存档的开关)。

用法:
  python tools/iso_build/fix_zh116_run.py --iso work/builds/GR_ZH111/GR_ZH111.iso \
      --tag base111 --state "work/temp/SLUS-20613 (7A361FB5).01.p2s" \
      --maxframes 3000 --snap 60 --live work/builds/GR_ZH116/temp/live_base111.txt

产物: work/builds/GR_ZH116/temp/dump_<tag>/
  snap_f%08u.png   截图   grlog.txt  钩子日志   pcsample.txt  PC 采样
  memwatch.bin     内存监视   drawlog.txt/drawlog 窗口
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
USER_MC = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'memcards')
OUTROOT = os.path.join(REPO, 'work', 'builds', 'GR_ZH116', 'temp')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--state', default=None)
    ap.add_argument('--maxframes', type=int, default=3000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--live', default=None)
    ap.add_argument('--input', default=None, help='frame-indexed -grinput file')
    ap.add_argument('--memwatch', action='append', default=[])
    ap.add_argument('--drawlog', default=None, help='<start> <end>')
    ap.add_argument('--pcsample', action='store_true')
    ap.add_argument('--memcards', default=None, help='dir (default: 用户 pcsx2-qt 的记忆卡副本)')
    ap.add_argument('--renderer', default='dx11')
    ap.add_argument('--keep', action='store_true', help='不删旧的 dump 目录')
    a = ap.parse_args()

    dump = os.path.join(OUTROOT, 'dump_' + a.tag)
    if os.path.isdir(dump) and not a.keep:
        shutil.rmtree(dump)
    os.makedirs(dump, exist_ok=True)

    mc = a.memcards
    if mc is None:
        mc = os.path.join(dump, 'mc')
        os.makedirs(mc, exist_ok=True)
        for f in ('Mcd001.ps2', 'Mcd002.ps2'):
            src = os.path.join(USER_MC, f)
            if os.path.isfile(src) and not os.path.isfile(os.path.join(mc, f)):
                shutil.copy2(src, os.path.join(mc, f))

    args = [GS, '-grdumpdir', dump, '-grsnap', str(a.snap),
            '-grmaxframes', str(a.maxframes), '-grscanframes', '1000000',
            '-grmemcards', mc, '-renderer', a.renderer]
    if a.state:
        args += ['-grstate', os.path.abspath(a.state)]
    if a.live:
        args += ['-grinputlive', os.path.abspath(a.live)]
    if a.input:
        args += ['-grinput', os.path.abspath(a.input)]
    if a.pcsample:
        args += ['-grpcsample', '1']
    for m in a.memwatch:
        args += ['-grmemwatch'] + m.split()
    if a.drawlog:
        args += ['-grdrawwin'] + a.drawlog.split()
    args += ['--', os.path.abspath(a.iso)]

    print('RUN: ' + ' '.join('"%s"' % x if ' ' in x else x for x in args))
    t0 = time.time()
    r = subprocess.run(args, cwd=os.path.dirname(GS))
    print('exit=%d elapsed=%.0fs dump=%s' % (r.returncode, time.time() - t0, dump))
    return r.returncode


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
