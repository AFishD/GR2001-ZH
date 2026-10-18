# -*- coding: utf-8 -*-
r"""run_rep.py -- 复现批次 (顺序与第一批**相反**, 用来抵消"谁先跑谁吃亏"的顺序效应)。

第一批: zh113b -> en_orig    (zh113b 432.2 s / en_orig 345.6 s)
本批  : en_orig -> zh113b_fix -> zh113b

每个手臂由 run_arm.py 负责 (等零 pcsx2 进程 / 全新记忆卡 / RUN.txt / 外来实例采样)。
"""
import argparse
import os
import subprocess
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'tools')
RUNNER = os.path.join(TOOLS, 'run_arm.py')

ARMS = {
    'zh113b': ('GR_ZH113b', r'work\builds\GR_ZH113b\GR_ZH113b.iso'),
    'en_orig': ('GR_EN_ORIG', r'work\builds\GR_EN_ORIG\GR_EN_ORIG.iso'),
    'zh113b_fix': ('GR_ZH113b_fix', r'work\builds\GR_ZH113b_fix\GR_ZH113b_fix.iso'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--order', default='en_orig,zh113b_fix,zh113b')
    ap.add_argument('--tag', default='rep2')
    ap.add_argument('--frames', type=int, default=32000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--perf', type=int, default=1)
    ap.add_argument('--nav', default='nav_play.txt')
    ap.add_argument('--wait-clear-s', type=int, default=3600)
    a = ap.parse_args()

    for name in a.order.split(','):
        name = name.strip()
        if name not in ARMS:
            raise SystemExit('未知手臂: %s' % name)
        tag, rel = ARMS[name]
        iso = os.path.join(REPO, rel)
        cmd = [sys.executable, RUNNER, '--arm', tag, '--iso', iso,
               '--frames', str(a.frames), '--snap', str(a.snap),
               '--nav', a.nav, '--perf', str(a.perf), '--tag', a.tag,
               '--wait-clear-s', str(a.wait_clear_s)]
        print('#' * 78, flush=True)
        print('### REPEAT ARM %s : %s   (tag=%s)' % (name, iso, a.tag), flush=True)
        print('#' * 78, flush=True)
        r = subprocess.run(cmd, cwd=REPO)
        print('### ARM %s runner exit=%d' % (name, r.returncode), flush=True)
    print('### ALL REPEAT ARMS DONE', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
