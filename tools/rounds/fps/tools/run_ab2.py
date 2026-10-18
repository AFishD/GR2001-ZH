# -*- coding: utf-8 -*-
r"""run_ab2.py -- 第三批 A/B: 用 **v3 输入表** (真进关卡: 射击 / 暂停存读档 / 小队页面候选键)。

顺序故意与第一批相反: 第一批 zh113b -> en_orig, 本批 en_orig -> zh113b -> zh113b_fix
⇒ 两张盘各当过一次"先跑", 顺序效应可对消; zh113b_fix 做 1 字节补丁的阴性对照。

用法: python work\builds\GR_FPS\tools\run_ab2.py [--frames 32000] [--nav nav_play_v3.txt]
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
    ap.add_argument('--order', default='en_orig,zh113b,zh113b_fix')
    ap.add_argument('--tag', default='v3')
    ap.add_argument('--frames', type=int, default=32000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--perf', type=int, default=1)
    ap.add_argument('--nav', default='nav_play_v3.txt')
    ap.add_argument('--wait-clear-s', type=int, default=5400)
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
        print('### V3 ARM %s : %s   (nav=%s tag=%s)' % (name, iso, a.nav, a.tag), flush=True)
        print('#' * 78, flush=True)
        r = subprocess.run(cmd, cwd=REPO)
        print('### ARM %s runner exit=%d' % (name, r.returncode), flush=True)
    print('### ALL V3 ARMS DONE', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
