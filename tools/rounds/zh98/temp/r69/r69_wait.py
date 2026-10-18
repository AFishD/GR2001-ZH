# -*- coding: utf-8 -*-
r"""r69_wait.py — 等模拟器空出来再跑一次采集 (单实例纪律: 绝不杀别人的实例)。

轮询 pcsx2-gsrunner 进程数; 为 0 时立刻启动 r69_run.py。
r69_run.py 自己也会再查一次 (双保险), 若仍被占用就退出并等待下一轮。

用法: python r69_wait.py <tag> <iso> <sf|brief> [--maxwait S] [--maxframes N]
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
REPO = HERE
while not os.path.isdir(os.path.join(REPO, 'tools', 'capture')):
    nxt = os.path.dirname(REPO)
    assert nxt != REPO, 'repo root not found from %s' % HERE
    REPO = nxt
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')


def busy():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | '
                        'Measure-Object).Count'],
                       capture_output=True, text=True)
    try:
        return int((r.stdout or '0').strip() or '0')
    except ValueError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('iso')
    ap.add_argument('mode')
    ap.add_argument('--maxwait', type=int, default=3600)
    ap.add_argument('--maxframes', type=int, default=40000)
    ap.add_argument('--tries', type=int, default=6, help='被抢占后最多重试几轮')
    ap.add_argument('--extra', default='', help='透传给 r69_run.py 的额外参数 (空格分隔)')
    a = ap.parse_args()
    extra = [x for x in a.extra.split() if x]
    t0 = time.time()
    attempt = 0
    tries = 0
    while time.time() - t0 < a.maxwait:
        attempt += 1
        if not os.path.isfile(GS):
            print('[wait] %s  第 %d 次: pcsx2-gsrunner.exe 不在 (同事正在重建模拟器), 等 30 s'
                  % (time.strftime('%H:%M:%S'), attempt), flush=True)
            time.sleep(30)
            continue
        if busy():
            n = busy()
            print('[wait] %s  第 %d 次: 有 %d 个 pcsx2-gsrunner 在跑, 等 25 s'
                  % (time.strftime('%H:%M:%S'), attempt, n), flush=True)
            time.sleep(25)
            continue
        tries += 1
        print('[go  ] %s  模拟器空闲 ⇒ 启动 %s / %s (第 %d/%d 次)'
              % (time.strftime('%H:%M:%S'), a.iso, a.tag, tries, a.tries), flush=True)
        rc = subprocess.call([PY, os.path.join(HERE, 'r69_run.py'),
                              a.tag, a.iso, a.mode, '--maxframes', str(a.maxframes)] + extra)
        print('[done] rc=%d tag=%s' % (rc, a.tag), flush=True)
        if rc == 0:
            return 0
        if tries >= a.tries:
            print('[giveup] %s 连续 %d 次未跑完 (多半被别人的 nav_hook Stop-Process 抢掉)'
                  % (a.tag, tries), flush=True)
            return 2
        print('[retry] 本轮失败/被抢占, 20 s 后再试', flush=True)
        time.sleep(20)
    print('[timeout] 等不到空闲模拟器 (%.0f s)' % (time.time() - t0))
    return 3


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
