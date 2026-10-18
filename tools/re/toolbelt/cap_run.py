# -*- coding: utf-8 -*-
r"""cap_run.py -- Step 4: 用**任务书给定的原命令**跑一次 pcsx2-gsrunner (串行独占)

    python tools/re/toolbelt/cap_run.py --iso <iso> --dump <dir> [--nav tools\capture\nav_menu_only.txt]

命令 (逐字, 不加任何额外旗标):
  pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30
      -grinput <nav> -grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>

纪律: 跑前/跑后都确认没有残留 pcsx2-gsrunner; 日志在运行中被独占, 本脚本只等进程退出后才返回;
      exit code **只作记录, 不作判据** (判据见 cap_results.py)。
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


def procs():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2-gsrunner.exe', '/NH'],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        txt = out.stdout.decode('utf-8', 'replace')
        return [l for l in txt.splitlines() if 'pcsx2-gsrunner' in l]
    except Exception as e:                                            # noqa: BLE001
        return ['<tasklist 失败: %s>' % e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--dump', required=True)
    ap.add_argument('--nav', default=os.path.join(REPO, 'tools', 'capture', 'nav_menu_only.txt'))
    ap.add_argument('--maxframes', default='6000')
    ap.add_argument('--snap', default='30')
    ap.add_argument('--wait-first', action='store_true',
                    help='若有别的实例在跑就等它退出 (默认直接中止, 保证"一次只跑一个")')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    iso = os.path.abspath(a.iso)
    dump = os.path.abspath(a.dump)
    mc = os.path.join(dump, 'mc')
    assert os.path.isfile(iso), iso
    p = procs()
    if p:
        if not a.wait_first:
            raise SystemExit('!! 已有 pcsx2-gsrunner 在跑, 拒绝并发:\n  %s' % '\n  '.join(p))
        while p:
            print('[wait] 等待已有实例退出: %s' % p[0], flush=True)
            time.sleep(20)
            p = procs()
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(mc, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        src = os.path.join(MC, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(mc, f))
    args = [GS, '-grdumpdir', dump, '-grmaxframes', a.maxframes, '-grsnap', a.snap,
            '-grinput', a.nav, '-grmemcards', mc, '-logfile',
            os.path.join(dump, 'emulog.txt'), '--', iso]
    print('[run] %s' % ' '.join(args), flush=True)
    t0 = time.time()
    with open(os.path.join(dump, 'stdout.txt'), 'wb') as fh:
        r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=fh, stderr=subprocess.STDOUT)
    el = time.time() - t0
    print('[run] exit=%d elapsed=%.0fs dump=%s' % (r.returncode, el, dump))
    p = procs()
    print('[run] 跑后残留进程: %s' % (p if p else '无 ✓'))
    with open(os.path.join(dump, 'RUN.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('cmd = %s\nexit = %d\nelapsed_s = %.0f\npost_procs = %s\n'
                % (' '.join(args), r.returncode, el, p if p else 'none'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
