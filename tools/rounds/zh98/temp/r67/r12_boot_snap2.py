# -*- coding: utf-8 -*-
r"""r12_boot_snap2.py — **只开机 + 只按 START** 的实机取证 (round67 兜底路径 v2)。

为什么要它
----------
· `nav_hook.py` 的引导段是固定帧时序 (start×10 → **up×3 → cross@3250**), 而 round67 实拍
  发现它在"主菜单还没开始吃按键"的窗口里就把 up/cross 发完了 (钩子一直 =1, 三次 up 一动不动)
  ⇒ 到不了「开发访谈 1」。加上模拟器被并行任务反复抢占, 长时序随时被掐。
· `r11_boot_snap.py` (完全不按键) 则一直停在片头动画, 4500 帧还没进主菜单。

本版取中间路线: **只复刻引导段里"无害"的那部分 (一路 START 跳片头), 一个方向键/确认键都不发**,
并用内存钩子 `0x013379D0` 判"主菜单是否就绪"。探针字放在**主菜单条目**上
(见 `r10_boot_probe_text.py`) ⇒ 主菜单一出现就能截图, 不需要任何导航。

判定"就绪": 钩子值落进主菜单项号集合 {1,2,3,5,6,7,8,9} 且**连续 STABLE 帧不变**。

用法: python r12_boot_snap2.py <iso> <dumpdir> [--wait-quiet 12] [--shots 4]
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'capture'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import nav_hook as NH                                                    # noqa: E402

BOOT_STARTS = list(range(800, 2700, 200))       # 与 nav_hook 引导段同一张单子 (跳片头用)
STABLE = 90                                     # 钩子连续稳定多少帧算"主菜单就绪"
RETRY_AT = 9500                                 # 到这一帧还没进菜单 ⇒ 补几发 START


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('dump')
    ap.add_argument('--wait-quiet', type=int, default=12)
    ap.add_argument('--shots', type=int, default=4)
    ap.add_argument('--maxframes', type=int, default=14000)
    a = ap.parse_args()
    iso, dump = os.path.abspath(a.iso), os.path.abspath(a.dump)
    os.makedirs(dump, exist_ok=True)

    t0 = time.time()
    while (time.time() - t0) < a.wait_quiet * 60:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2*', '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True).stdout.lower()
        if 'pcsx2' not in r:
            break
        print('[wait] %s 仍有 emulator 进程' % time.strftime('%H:%M:%S'), flush=True)
        time.sleep(15)

    cmd = os.path.join(dump, 'live_r67boot.txt')
    open(cmd, 'w').close()
    print('[run ] %s 启动 (钩子 0x%08X, 只发 START)' % (time.strftime('%H:%M:%S'),
                                                      NH.MENU_SEL_ADDR), flush=True)
    emu = NH.Emu(iso, dump, cmd, [(NH.MENU_SEL_ADDR, 4, 1)], a.maxframes, 500)
    emu.start()
    ready, last, stable, pending, retried = None, None, 0, list(BOOT_STARTS), False
    try:
        while emu.alive():
            f, v = emu.sample()
            if f is None:
                time.sleep(0.05)
                continue
            if f >= a.maxframes:
                break
            if pending and f >= pending[0]:
                emu.tap('start')
                print('   [F%-6d 钩子=%-4s] >> start tap (跳片头)' % (f, v), flush=True)
                pending.pop(0)
                time.sleep(0.05)
                continue
            inmenu = v in NH.MENU_ROWS
            stable = stable + 1 if (inmenu and v == last) else 0
            last = v
            if stable >= STABLE:
                ready = f
                print('[menu] %s **主菜单就绪** @frame %d (钩子=%s, 连续稳定 %d 帧)'
                      % (time.strftime('%H:%M:%S'), f, v, stable), flush=True)
                break
            if not pending and not retried and f >= RETRY_AT:
                retried = True
                pending = [f + 200 * i for i in range(1, 6)]
                print('   [F%-6d 钩子=%-4s] 还没进菜单 ⇒ 再补 5 发 START' % (f, v), flush=True)
            f2, _ = emu.sample()
            emu.wait_frame((f2 or 0) + 15, timeout=180.0)
    finally:
        if ready is not None:
            for i in range(a.shots):
                emu.send('snap r67boot_menu%d' % i)
                fr, _v = emu.sample()
                print('[snap] r67boot_menu%d @frame %s' % (i, fr), flush=True)
                try:
                    emu.wait_frame((fr or 0) + 90, timeout=180.0)
                except Exception:                                        # noqa: BLE001
                    break
        else:
            print('[!!  ] 没等到主菜单 (最后钩子=%s)' % last, flush=True)
        emu.stop()
    shots = sorted(f for f in os.listdir(dump) if f.startswith('r67boot_menu'))
    print('[done] %d 张:' % len(shots))
    for f in shots:
        print('   %8d B  %s' % (os.path.getsize(os.path.join(dump, f)), f))


if __name__ == '__main__':
    main()
