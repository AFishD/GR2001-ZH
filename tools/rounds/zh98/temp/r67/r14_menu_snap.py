# -*- coding: utf-8 -*-
r"""r14_menu_snap.py — 用 **nav_hook 的原版引导段** 走到主菜单就截图 (round67 取证主路径 v4)。

前几版踩的坑 (都记下来, 免得再犯):
  · v1 完全不按键 → 一直放片头动画, 4500 帧还没进主菜单;
  · v2 只按 START  → 停在**「输入名字」**键盘页, 而那页上钩子 `0x013379D0` 恰好也稳定读 1
                    ⇒ 被误判成"主菜单就绪";
  · v3 想用 up 探针分辨 → 键盘页上 up 只移动字母光标, 钩子纹丝不动, 一直卡着。
  · ★ 真正的读法: `nav_hook.py` 引导段里的 **up×3 → cross@3250** 就是**在「输入名字」页上**
    把光标挪到「确认」并按下它 (所以 v2/v3 缺了这三下 up 就永远过不去);
    之后 nav_hook 会等到 **frame 8000** 才做握手 —— 我第一次跑 nav_hook 是在 **frame 5649
    被外部掐掉的, 根本没活到握手**.

本脚本 = nav_hook 的引导段 + 握手 + 截图, **到主菜单就收**, 不进入特别收录
⇒ 占用窗口从 ~350 s 压到 ~130 s, 在"模拟器被反复抢占"的环境里更容易活下来。

用法: python r14_menu_snap.py <iso> <dumpdir> [--wait-quiet 10] [--shots 3]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('dump')
    ap.add_argument('--wait-quiet', type=int, default=10)
    ap.add_argument('--shots', type=int, default=3)
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

    cmd = os.path.join(dump, 'live_r67menu.txt')
    open(cmd, 'w').close()
    print('[run ] %s 启动 (nav_hook 原版引导段)"' % time.strftime('%H:%M:%S'), flush=True)
    emu = NH.Emu(iso, dump, cmd, [(NH.MENU_SEL_ADDR, 4, 1)], a.maxframes, 500)
    emu.start()
    hot = False
    try:
        for f in NH.BOOT_STARTS:
            emu.wait_frame(f)
            emu.tap('start')
        for f in NH.BOOT_UPS:
            emu.wait_frame(f)
            emu.tap('up')
        emu.wait_frame(NH.BOOT_CROSS)
        emu.tap('cross')
        print('   [boot] start×%d → up×3 → cross 发完 (跳片头 + 打发「输入名字」页)'
              % len(NH.BOOT_STARTS), flush=True)
        # ★ 不写死 frame 8000: 机器被并行任务抢占时, 游戏启动在**帧轴上会后移**
        #   (CDVD 读延迟随负载漂)。这里一路小步长探到 maxframes, 直到钩子对 up 有反应。
        for probe in range(40):
            f0, v0 = emu.sample(NH.MENU_SEL_ADDR)
            if f0 is None:
                time.sleep(0.05)
                continue
            if f0 >= a.maxframes:
                break
            emu.tap('up')
            emu.wait_frame((f0 or 0) + 120, timeout=200.0)
            f1, v1 = emu.sample(NH.MENU_SEL_ADDR)
            print('   [握手 #%-2d @F%-6s] 钩子 %s → %s' % (probe, f0, v0, v1), flush=True)
            if v1 != v0 and v1 in NH.MENU_ROWS:
                hot = True
                emu.tap('down')                       # 还原到原选中项
                emu.wait_frame((emu.sample()[0] or 0) + 120, timeout=200.0)
                print('   [握手 #%d] **主菜单已激活** (还原后钩子=%s)'
                      % (probe, emu.sample(NH.MENU_SEL_ADDR)[1]), flush=True)
                break
            emu.wait_frame((emu.sample()[0] or 0) + 480, timeout=200.0)
        if hot:
            for i in range(a.shots):
                emu.send('snap r67menu_%d' % i)
                fr, _v = emu.sample()
                print('[snap] r67menu_%d @frame %s' % (i, fr), flush=True)
                emu.wait_frame((fr or 0) + 90, timeout=180.0)
        else:
            print('[!!  ] 主菜单钩子不响应', flush=True)
    except Exception as e:                                               # noqa: BLE001
        print('[!!  ] %s: %s' % (type(e).__name__, e), flush=True)
    finally:
        try:
            emu.proc.terminate()
        except Exception:                                                # noqa: BLE001
            pass
    shots = sorted(f for f in os.listdir(dump) if f.startswith('r67menu_'))
    print('[done] %d 张:' % len(shots))
    for f in shots:
        print('   %8d B  %s' % (os.path.getsize(os.path.join(dump, f)), f))


if __name__ == '__main__':
    main()
