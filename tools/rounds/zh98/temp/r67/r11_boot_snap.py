# -*- coding: utf-8 -*-
r"""r11_boot_snap.py — **只开机、不按键**的实机取证 (round67 的兜底路径)。

为什么需要它: `nav_hook.py` 的引导段是固定帧时序, 在"主菜单还没吃按键"的窗口里就把
up/cross 发完了 ⇒ 到不了「开发访谈 1」。而本轮模拟器又被并行任务反复抢占, 长时序随时被掐。
本脚本把探针放在**主菜单**(见 r10_boot_probe_text.py), 于是**一个按键都不用发** ——
开机 → 每 250 帧自动截图 → 到点自退。占用窗口 ~70 s。

用法: python r11_boot_snap.py <iso> <dumpdir> [--maxframes 4500] [--snap 250] [--wait-quiet 12]
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')


def pcsx2():
    """当前所有 pcsx2 进程 (名称, pid)。"""
    out = []
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2*', '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True, timeout=30)
        for line in r.stdout.splitlines():
            if 'pcsx2' in line.lower():
                p = [x.strip('"') for x in line.split('","')]
                out.append((p[0], p[1]))
    except Exception:                                                     # noqa: BLE001
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('dump')
    ap.add_argument('--maxframes', type=int, default=4500)
    ap.add_argument('--snap', type=int, default=250)
    ap.add_argument('--wait-quiet', type=int, default=12, help='等静默窗口的分钟数')
    a = ap.parse_args()
    iso, dump = os.path.abspath(a.iso), os.path.abspath(a.dump)

    t0 = time.time()
    while (time.time() - t0) < a.wait_quiet * 60:
        ps = pcsx2()
        if not ps:
            break
        print('[wait] %s 仍有 %d 个 emulator 进程: %s'
              % (time.strftime('%H:%M:%S'), len(ps), ps), flush=True)
        time.sleep(15)
    ps = pcsx2()
    print('[run ] %s emulator 进程 %d 个; 启动只开机取证 (maxframes=%d snap=%d)'
          % (time.strftime('%H:%M:%S'), len(ps), a.maxframes, a.snap), flush=True)

    os.makedirs(dump, exist_ok=True)
    mc = os.path.join(dump, 'mc')
    os.makedirs(mc, exist_ok=True)
    cmd = [GS, '-grdumpdir', dump, '-grsnap', str(a.snap),
           '-grmaxframes', str(a.maxframes), '-grmemcards', mc,
           '-renderer', 'dx11', '--', iso]
    with open(os.path.join(dump, 'boot_cmd.txt'), 'w', encoding='utf-8') as f:
        f.write(' '.join(cmd) + '\n')
    t1 = time.time()
    p = subprocess.Popen(cmd, cwd=os.path.dirname(GS))
    rc = p.wait()
    print('[done] rc=%s 耗时 %.0f s' % (rc, time.time() - t1), flush=True)
    shots = sorted((int(f.split('f')[1][:-4]), f) for f in os.listdir(dump)
                   if f.startswith('snap_f') and f.endswith('.png'))
    print('[snap] %d 张:' % len(shots))
    for fr, f in shots:
        print('   frame %6d  %8d B  %s' % (fr, os.path.getsize(os.path.join(dump, f)), f))


if __name__ == '__main__':
    main()
