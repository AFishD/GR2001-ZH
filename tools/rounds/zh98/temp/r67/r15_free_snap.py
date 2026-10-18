# -*- coding: utf-8 -*-
r"""r15_free_snap.py — 开机 + 原版引导段 + **定期连拍** (round67 取证路径 v5, 最稳的一版)。

前几版的教训: 任何"固定帧 + 精确握手"的组合在**被并行任务抢占的机器**上都会错位
(游戏启动在帧轴上会后移)。本版干脆**不做握手**:
  · 复刻 nav_hook 引导段 (start×10 → up×3 → cross) —— 这一段的作用是跳片头 + 打发
    「输入名字」页 (实拍证明 up×3 → cross 会在名字框里打出一个字母, 「确认」按钮随之点亮);
  · 之后 `-grsnap 250` 一路连拍 (每 250 帧一张), 中途在若干帧上补 `down`+`cross`
    去按那个「确认」, 好把流程推进到主菜单;
  · 到 maxframes 自退 ⇒ 事后从连拍里挑"新字可见"的那几张。

探针字放在 **「输入名字」页 (无存盘时开局自动弹) + 主菜单** 两处 (见 r10_boot_probe_text.py)
⇒ 无论停在哪一页, 都有新字可看。

用法: python r15_free_snap.py <iso> <dumpdir> [--wait-quiet 5] [--maxframes 20000]
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

# 在这些帧上按「确认」: 「输入名字」页里 down 走到确认按钮, cross 按下
CONFIRM_AT = (4200, 6000, 7800, 9600, 11400, 13200, 15000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('dump')
    ap.add_argument('--wait-quiet', type=int, default=5)
    ap.add_argument('--maxframes', type=int, default=20000)
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

    cmd = os.path.join(dump, 'live_r67free.txt')
    open(cmd, 'w').close()
    print('[run ] %s 启动; maxframes=%d, 连拍间隔 250 帧' % (time.strftime('%H:%M:%S'), a.maxframes),
          flush=True)
    emu = NH.Emu(iso, dump, cmd, [(NH.MENU_SEL_ADDR, 4, 1)], a.maxframes, 250)
    emu.start()
    pend = list(CONFIRM_AT)
    try:
        for f in NH.BOOT_STARTS:
            emu.wait_frame(f)
            emu.tap('start')
        for f in NH.BOOT_UPS:
            emu.wait_frame(f)
            emu.tap('up')
        emu.wait_frame(NH.BOOT_CROSS)
        emu.tap('cross')
        print('   [boot] start×%d → up×3 → cross 发完' % len(NH.BOOT_STARTS), flush=True)
        while emu.alive():
            fr, v = emu.sample()
            if fr is None:
                time.sleep(0.05)
                continue
            if fr >= a.maxframes:
                break
            if pend and fr >= pend[0]:
                print('   [F%-6d 钩子=%-4s] >> down + cross (按「确认」推进)' % (fr, v), flush=True)
                emu.tap('down')
                time.sleep(0.05)
                emu.tap('cross')
                pend.pop(0)
                emu.wait_frame(fr + 150, timeout=200.0)
                continue
            if fr % 1000 < 20:
                print('   [F%-6d 钩子=%-4s] ...' % (fr, v), flush=True)
            emu.wait_frame(fr + 60, timeout=200.0)
    except Exception as e:                                               # noqa: BLE001
        print('[!!  ] %s: %s' % (type(e).__name__, e), flush=True)
    finally:
        try:
            emu.proc.terminate()
        except Exception:                                                # noqa: BLE001
            pass
    shots = sorted((int(f.split('f')[1][:-4]), f) for f in os.listdir(dump)
                   if f.startswith('snap_f') and f.endswith('.png'))
    print('[done] 连拍 %d 张 (最大 frame %s):' % (len(shots), shots[-1][0] if shots else '-'))
    for fr, f in shots:
        print('   frame %6d  %8d B  %s' % (fr, os.path.getsize(os.path.join(dump, f)), f))


if __name__ == '__main__':
    main()
