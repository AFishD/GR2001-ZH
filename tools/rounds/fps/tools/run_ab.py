# -*- coding: utf-8 -*-
r"""run_ab.py -- 串行跑完整个 A/B (严禁并发: 一个跑完再起下一个)。

手臂顺序 (可用 --arms 覆盖):
  zh113b    work\builds\GR_ZH113b\GR_ZH113b.iso        <- 用户报障的那张盘
  en_orig   work\builds\GR_EN_ORIG\GR_EN_ORIG.iso      <- 英文原盘 (必须做的对照)
  zh113b_fix work\builds\GR_ZH113b_fix\GR_ZH113b_fix.iso <- 可选第三臂 (1 字节补丁版)

每个手臂都由 run_arm.py 负责: 等"零 pcsx2 进程" -> 全新记忆卡副本 -> 跑 ->
记录 RUN.txt (exit/elapsed/pre/post 进程/外来实例重叠采样) -> 绝不动别人的进程。
"""
import argparse
import io
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
    ap.add_argument('--arms', default='zh113b,en_orig')
    ap.add_argument('--frames', type=int, default=40000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--perf', type=int, default=1)
    ap.add_argument('--nav', default='nav_play.txt')
    ap.add_argument('--wait-clear-s', type=int, default=2400)
    a = ap.parse_args()

    for name in a.arms.split(','):
        name = name.strip()
        if name not in ARMS:
            raise SystemExit('未知手臂: %s (可选 %s)' % (name, list(ARMS)))
        tag, rel = ARMS[name]
        iso = os.path.join(REPO, rel)
        cmd = [sys.executable, RUNNER, '--arm', tag, '--iso', iso,
               '--frames', str(a.frames), '--snap', str(a.snap),
               '--nav', a.nav, '--perf', str(a.perf),
               '--wait-clear-s', str(a.wait_clear_s)]
        print('#' * 78, flush=True)
        print('### ARM %s : %s' % (name, iso), flush=True)
        print('#' * 78, flush=True)
        r = subprocess.run(cmd, cwd=REPO)
        print('### ARM %s runner exit=%d' % (name, r.returncode), flush=True)
    print('### ALL ARMS DONE', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
