# -*- coding: utf-8 -*-
r"""r13_boot_snap3.py — **只开机 + 只按 START + 一次握手** 的实机取证 (round67 兜底路径 v3)。

v2 (`r12_boot_snap2.py`) 的坑: 无存盘时游戏先弹**「输入名字」**键盘页, 而内存钩子
`0x013379D0` 在那页上**恰好也稳定读 1** ⇒ 被误判成"主菜单就绪"(实拍 `r67boot_menu1.png`)。
v3 加上 `nav_hook.py` 阶段2 的那套**握手**: 按 up 看钩子是否 1→9 (主菜单 9 项回绕),
再按 down 看是否 9→1; 两次都对才算主菜单。不对 ⇒ 发 cross 打发掉挡路的页(名字页/提示框), 重试。

全程**不发方向键去导航**, 只是用 up/down 做一次"这页是不是主菜单"的探针, 并立刻还原。

用法: python r13_boot_snap3.py <iso> <dumpdir> [--wait-quiet 12] [--shots 3]
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

BOOT_STARTS = list(range(800, 2700, 200))
STABLE = 60


def wait_stable(emu, need=STABLE, maxt=12000):
    """等钩子连续 need 帧落在主菜单项号集合里。返回 (frame, value) 或 (None, last)。"""
    last, stable = None, 0
    while emu.alive():
        f, v = emu.sample()
        if f is None:
            time.sleep(0.05)
            continue
        if f >= maxt:
            return None, last
        stable = stable + 1 if (v in NH.MENU_ROWS and v == last) else 0
        last = v
        if stable >= need:
            return f, v
        f2, _ = emu.sample()
        emu.wait_frame((f2 or 0) + 12, timeout=180.0)
    return None, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('dump')
    ap.add_argument('--wait-quiet', type=int, default=12)
    ap.add_argument('--shots', type=int, default=3)
    ap.add_argument('--maxframes', type=int, default=16000)
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
    print('[run ] %s 启动 (钩子 0x%08X)' % (time.strftime('%H:%M:%S'), NH.MENU_SEL_ADDR), flush=True)
    emu = NH.Emu(iso, dump, cmd, [(NH.MENU_SEL_ADDR, 4, 1)], a.maxframes, 500)
    emu.start()
    ok = False
    try:
        for sk in BOOT_STARTS:
            emu.wait_frame(sk, timeout=300.0)
            emu.tap('start')
        print('   [boot] %d 发 START 发完 (跳片头/跳过提示)' % len(BOOT_STARTS), flush=True)
        for attempt in range(1, 9):
            f, v = wait_stable(emu)
            if f is None:
                print('   [握手 %d] 没等到稳定的菜单项号 (最后钩子=%s)' % (attempt, v), flush=True)
                break
            print('   [握手 %d] @F%d 钩子=%s 稳定 ⇒ 按 up 试 1→9' % (attempt, f, v), flush=True)
            emu.tap('up')
            time.sleep(0.1)
            f2, v2 = wait_stable(emu) or (None, None)
            f2, v2 = emu.sample()
            print('        up 后钩子=%s' % v2, flush=True)
            if v2 == 9 and v == 1:
                emu.tap('down')
                time.sleep(0.1)
                _f3, v3 = emu.sample()
                print('        down 后钩子=%s' % v3, flush=True)
                if v3 == 1:
                    ok = True
                    print('   [握手 %d] **确认是主菜单** (1→9→1)' % attempt, flush=True)
                    break
            print('   [握手 %d] 不是主菜单 ⇒ 发 cross 打发掉挡路的页' % attempt, flush=True)
            emu.tap('cross')
            time.sleep(0.1)
            emu.wait_frame((emu.sample()[0] or 0) + 150, timeout=300.0)
        if ok:
            for i in range(a.shots):
                emu.send('snap r67boot_menu%d' % i)
                fr, _v = emu.sample()
                print('[snap] r67boot_menu%d @frame %s' % (i, fr), flush=True)
                emu.wait_frame((fr or 0) + 90, timeout=180.0)
        else:
            print('[!!  ] 没能确认主菜单', flush=True)
    except Exception as e:                                               # noqa: BLE001
        print('[!!  ] %s: %s' % (type(e).__name__, e), flush=True)
    finally:
        try:
            emu.proc.terminate()
        except Exception:                                                # noqa: BLE001
            pass
    shots = sorted(f for f in os.listdir(dump) if f.startswith('r67boot_menu'))
    print('[done] %d 张:' % len(shots))
    for f in shots:
        print('   %8d B  %s' % (os.path.getsize(os.path.join(dump, f)), f))


if __name__ == '__main__':
    main()
