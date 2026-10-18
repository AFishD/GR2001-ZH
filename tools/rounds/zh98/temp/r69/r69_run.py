# -*- coding: utf-8 -*-
r"""r69_run.py — 本轮 (r69) 专用实机采集驱动。

为什么不用 tools/capture/nav_hook.py 本体: 它把 dump 目录写死成
work/builds/<version>/temp/dump_<tag>。本轮只允许写 work/builds/GR_ZH115/,
而基线盘是 work/builds/GR_ZH111/GR_ZH111.iso (只读) ⇒ 这里复用 nav_hook 的
Emu 类与闭环函数, 但**自己指定 dump 目录**, 并把 GR_ZH111 的基线也落在
work/builds/GR_ZH115/temp/ 下, 便于逐像素配对。

模式
  sf     : 主菜单 → 特别收录 → 访谈 → 开发访谈 1 (闭环导航, 抄 nav_hook 的时序)
  brief  : 主菜单 → 战术演习 → 简报页 (固定时序 nav_p2.txt, 与 run_brief2.py 同口径)

用法:
  python r69_run.py <tag> <iso> <sf|brief> [--maxframes N] [--snap N]

单实例: 起跑前检查 pcsx2-gsrunner; 有别的实例在跑就拒绝启动 (不杀别人)。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, 'tools', 'capture')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)

sys.path.insert(0, os.path.join(REPO, 'tools', 'capture'))
import nav_hook as N                                                       # noqa: E402

GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
OUTROOT = os.path.join(REPO, 'work', 'builds', 'GR_ZH115', 'temp')
NAV_P2 = os.path.join(REPO, 'tools', 'capture', 'nav_p2.txt')

# GR_ZH98..GR_ZH111 实测恒定的 5 个 RSHTML 实例 (见 docs/REPORT_sf_nowrap.md §2)
# ★ 前两个区间是 nav_hook 的闭环钩子 (主菜单选中项 / 特别收录列表标志位),
#   必须一起 watch —— emu.sample(addr) 只能读"被 watch 的区间"。
RSHTML_WATCH = [(0x0124A6A4, 0x120, 1),      # RSHTML#1: SF 介绍框 (内页时 W=270 H=190)
                (0x0124B650, 0x120, 1),      # RSHTML#4: 同为 270x190
                (0x01304E10, 0x120, 1)]      # RSHTML#5: 270x156


def busy():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | '
                        'Measure-Object).Count'],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip() or '0')
    except ValueError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('iso')
    ap.add_argument('mode', choices=['sf', 'brief'])
    ap.add_argument('--maxframes', type=int, default=40000)
    ap.add_argument('--snap', type=int, default=500)
    ap.add_argument('--no-watch', action='store_true')
    ap.add_argument('--sf-idx', type=int, default=None,
                    help='特别收录列表目标项下标 (默认 7=访谈; 4=奖章, 3=武器, 0=影片)')
    a = ap.parse_args()

    if busy():
        sys.exit('!! 已有 pcsx2-gsrunner 在跑 —— 本轮单实例纪律: 不启动, 不杀别人')
    iso = os.path.abspath(a.iso)
    assert os.path.isfile(iso), iso
    dump = os.path.join(OUTROOT, 'dump_%s' % a.tag)
    cmd = os.path.join(OUTROOT, 'live_%s.txt' % a.tag)
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(os.path.join(dump, 'mc'))
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(dump, 'mc', f))
    open(cmd, 'w').close()

    watches = [(N.MENU_SEL_ADDR, 4, 1), (N.SF_SEL_ADDR, N.SF_SEL_SIZE, 1)]
    if not a.no_watch:
        watches += RSHTML_WATCH
    emu = N.Emu(iso, dump, cmd, watches, a.maxframes, a.snap)
    # brief 模式用固定输入脚本 (-grinput), 与 run_brief2.py 同口径
    base_start = emu.start

    def start_with_nav():
        assert base_start is not None
        orig_popen = subprocess.Popen

        def popen(args, **kw):
            if a.mode == 'brief':
                i = args.index('-grdumpdir')
                args = (args[:i] + ['-grinput', NAV_P2, '-grdrawwin', '8400', '10600'] + args[i:])
            print('ARGS: %s' % ' '.join(args), flush=True)
            return orig_popen(args, **kw)
        subprocess.Popen = popen
        try:
            base_start()
        finally:
            subprocess.Popen = orig_popen
    start_with_nav()
    print('pid = %d  dump = %s  mode = %s' % (emu.proc.pid, dump, a.mode), flush=True)
    t0 = time.time()
    ok, reason = False, ''
    try:
        if a.mode == 'brief':
            # 全固定时序 (nav_p2.txt): 主菜单 f~3400, 简报页 f~8650..10300
            plan = [(3300, 'snap r69_%s_filesel' % a.tag),
                    (4200, 'dump r69_%s_menu' % a.tag),
                    (4400, 'snap r69_%s_menu' % a.tag),
                    (8600, 'dump r69_%s_pre' % a.tag),
                    (8750, 'dump r69_%s_brief' % a.tag),
                    (8800, 'snap r69_%s_brief' % a.tag),
                    (9400, 'dump r69_%s_brief_b' % a.tag),
                    (9450, 'snap r69_%s_brief_b' % a.tag),
                    (10200, 'snap r69_%s_late' % a.tag)]
            for fr, c in plan:
                emu.wait_frame(fr)
                emu.send(c)
            emu.wait_frame(10400)
            ok, reason = True, 'brief 固定时序跑完'
        else:
            print('\n[阶段1] 引导: start×10 → up×3 → cross', flush=True)
            for f in N.BOOT_STARTS:
                emu.wait_frame(f)
                emu.tap('start')
            for f in N.BOOT_UPS:
                emu.wait_frame(f)
                emu.tap('up')
            emu.wait_frame(N.BOOT_CROSS)
            emu.tap('cross')
            print('\n[阶段2] 主菜单: 取证 + 握手', flush=True)
            emu.wait_frame(4600)
            emu.send('dump r69_%s_menu' % a.tag)
            emu.send('snap r69_%s_menu' % a.tag)
            emu.wait_frame(5200)
            emu.send('snap r69_%s_menu_b' % a.tag)
            emu.wait_frame(8000)
            hot = False
            for probe in range(8):
                f0, v0 = emu.sample(N.MENU_SEL_ADDR)
                emu.tap('up')
                emu.wait_frame((f0 or 0) + 120)
                f1, v1 = emu.sample(N.MENU_SEL_ADDR)
                print('   探测 #%d: 钩子 %s → %s' % (probe, v0, v1), flush=True)
                if v1 != v0 and v1 in N.MENU_ROWS:
                    hot = True
                    break
                emu.wait_frame((emu.sample()[0] or 0) + 800)
            if not hot:
                raise RuntimeError('主菜单钩子不响应')
            print('\n[阶段3] 闭环 → 特别收录', flush=True)
            if not N.closed_loop(emu, N.MENU_SEL_ADDR, N.MENU_ROWS, N.MENU_LABELS,
                                 N.MENU_TARGET_IDX, '主菜单'):
                raise RuntimeError('主菜单闭环失败')
            emu.wait_frame((emu.sample()[0] or 0) + 60)
            emu.send('snap r69_%s_menu_sf' % a.tag)
            emu.tap('cross')
            f_enter = emu.sample()[0] or 0
            sf_idx = N.SF_TARGET_IDX if a.sf_idx is None else a.sf_idx
            print('\n[阶段4] 特别收录列表 → %s (idx=%d)' % (N.SF_LABELS[sf_idx], sf_idx), flush=True)
            emu.wait_frame(f_enter + 3000)
            y0, row0 = N.snap_band(emu, 'sf_probe_a')
            hot = False
            for probe in range(10):
                fr0, _ = emu.sample()
                emu.tap('down')
                emu.wait_frame((fr0 or 0) + 250)
                y1, row1 = N.snap_band(emu, 'sf_probe_b')
                print('   探测 #%d: 金带 y=%s → %s (行 %s)' % (probe, y0, y1, row1), flush=True)
                if y1 is not None and y0 is not None and abs(y1 - y0) > 5:
                    hot = True
                    break
                emu.wait_frame((emu.sample()[0] or 0) + 1200)
                y0 = y1
            if not hot:
                raise RuntimeError('特别收录列表未激活')
            _, cur = N.snap_band(emu, 'sf_probe_c')
            if cur is None:
                raise RuntimeError('无法识别当前行')
            for _ in range(12):
                if cur == 1:
                    break
                fr0, _ = emu.region(N.SF_SEL_ADDR)
                emu.tap('up')
                emu.wait_frame((fr0 or 0) + 200)
                _, nrow = N.snap_band(emu, 'sf_up_probe')
                if nrow is None or nrow == cur:
                    emu.tap('up')
                    _, nrow = N.snap_band(emu, 'sf_up_probe2')
                if nrow is None or nrow == cur:
                    raise RuntimeError('up 连续两次未生效 (行 %s)' % cur)
                cur = nrow
            if cur != 1:
                raise RuntimeError('未能回到第 1 行')
            emu.send('dump r69_%s_sflist' % a.tag)
            emu.send('snap r69_%s_sflist' % a.tag)
            target_row = N.SF_ROWS[sf_idx]
            steps = 0
            while cur != target_row and steps < 15:
                ok_step, nrow, note = N.sf_press_down(emu, N.SF_SEL_ADDR, cur, 'sf')
                steps += 1
                print('   down #%d: %s' % (steps, note), flush=True)
                if ok_step:
                    cur = nrow
                else:
                    if nrow is not None and nrow != cur:
                        cur = nrow
                        continue
                    ok_step, nrow, note = N.sf_press_down(emu, N.SF_SEL_ADDR, cur, 'sf_retry')
                    if ok_step:
                        cur = nrow
                    else:
                        raise RuntimeError('down 连续两次无效 (行 %s)' % cur)
            if cur != target_row:
                raise RuntimeError('未到达第 %d 行 (停在 %s)' % (target_row, cur))
            print('\n[阶段5] 打开「%s」并取证' % N.SF_LABELS[sf_idx], flush=True)
            emu.tap('cross')
            f_arr = (emu.sample()[0] or 0) + 1500
            emu.wait_frame(f_arr)
            emu.send('drawwin %d %d' % (f_arr - 1200, f_arr + 1800))
            emu.send('snap r69_%s_page' % a.tag)
            emu.wait_frame(f_arr + 260)
            emu.send('dump r69_%s_page' % a.tag)
            emu.wait_frame(f_arr + 700)
            emu.send('snap r69_%s_page_b' % a.tag)
            emu.wait_frame(f_arr + 1200)
            emu.send('snap r69_%s_page_c' % a.tag)
            ok, reason = True, '到达 开发访谈 1'
    except Exception as e:                                              # noqa: BLE001
        ok, reason = False, '%s: %s' % (type(e).__name__, e)
        print('\n!! 中断: %s' % reason, flush=True)
        try:
            emu.send('snap r69_%s_last' % a.tag)
            emu.wait_frame((emu.sample()[0] or 0) + 120)
        except Exception:                                               # noqa: BLE001
            pass
    try:
        f, _ = emu.sample()
        if f is not None and f < a.maxframes - 60:
            emu.proc.terminate()
    except Exception:                                                   # noqa: BLE001
        pass
    try:
        emu.proc.wait(timeout=120)
    except Exception:                                                   # noqa: BLE001
        emu.proc.kill()
    el = time.time() - t0
    print('\n结果: %s — %s   耗时 %.0f s   dump=%s' % ('★ 成功' if ok else '✗ 失败', reason, el, dump))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
