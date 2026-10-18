# -*- coding: utf-8 -*-
r"""runcap.py — round29 专用捕获器 (run_opt.py 的等价物, 但可控制 -grscanframes)

为什么需要它: 本机负载下引导耗时比历史轮次长得多 (历史导航假设 F7050 到主菜单,
本机 F9100 还在标题屏)。本脚本用于把 -grscanframes 等参数按历史成功批次对齐。

用法: runcap.py <tag> <iso> <nav> [maxframes] [snap] [drawwin0 drawwin1] [scanframes]
输出: work/builds/<版本>/temp/dump_<tag>/
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')


def main():
    tag, iso, nav = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    maxf = sys.argv[4] if len(sys.argv) > 4 else '11700'
    snap = sys.argv[5] if len(sys.argv) > 5 else '100'
    dw = sys.argv[6:8] if len(sys.argv) > 7 else []
    scanf = sys.argv[8] if len(sys.argv) > 8 else '4000'
    ver = os.path.basename(os.path.dirname(iso))
    temp = os.path.join(BUILDS, ver, 'temp')
    mcd = os.path.join(temp, 'mc')
    os.makedirs(mcd, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(mcd, f))
    dump = os.path.join(temp, 'dump_' + tag)
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    args = [GS, '-grdumpdir', dump, '-grscanframes', scanf,
            '-grsnap', snap, '-grmaxframes', maxf,
            '-grmemcards', mcd, '-grinput', nav]
    if dw:
        args = [GS, '-grdumpdir', dump, '-grdrawwin', dw[0], dw[1],
                '-grscanframes', scanf, '-grsnap', snap, '-grmaxframes', maxf,
                '-grmemcards', mcd, '-grinput', nav]
    args += ['-renderer', 'dx11', '--', iso]
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print('GS %s' % ' '.join(args[:12]))
    t0 = time.time()
    r = subprocess.run(args, cwd=os.path.dirname(GS))
    print('exit=%d elapsed=%.0fs dump=%s' % (r.returncode, time.time() - t0, dump))


main()
