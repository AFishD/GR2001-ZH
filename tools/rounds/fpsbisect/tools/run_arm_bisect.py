# -*- coding: utf-8 -*-
r"""run_arm_bisect.py -- GR_FPSBISECT 用的单臂运行器。

= 逐字复用 `work\builds\GR_FPS\tools\run_arm.py`（前一位性能执行者的配方），**只改两处**：
  (1) ROOT = work\builds\GR_FPSBISECT\out   —— 因为本轮的写入范围是 GR_FPSBISECT\**,
      GR_FPS\** 只读（工具与输入表只读复用）。
  (2) 起跑前"等零 pcsx2 进程"超时 -> **拒绝起跑**（写 RUN.txt 的 aborted=wait_timeout,
      exit 9），而不是像原版那样"仍被别人占着也硬跑" —— 硬跑出来的 fps 是污染读数，
      对本轮的结论没有价值。要硬跑请显式给 --force-contended。

纪律（沿用）：
  * 模拟器一次只跑一个实例 -> 跑前查 *pcsx2* 进程，有残留就等（不杀）
  * 日志被独占 -> 只在进程退出后才读
  * exit=0 不算证据 -> 记 frames / elapsed / TLB / Trap，以数字为准

用法:
  python work\builds\GR_FPSBISECT\tools\run_arm_bisect.py --arm HK_01 --iso <iso> \
      --frames 32000 --snap 60 --perf 1 --nav nav_play_v4.txt --tag fpsbisect
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import threading
import time

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC_TPL = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
ROOT = os.path.join(REPO, 'work', 'builds', 'GR_FPSBISECT', 'out')
# 输入表只读复用 GR_FPS\tools 下的既有文件（保证与上一轮逐字相同的导航）
TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'tools')


def pcsx2_procs(exclude_marker=None):
    out = []
    try:
        ps = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*pcsx2*' } | "
             "ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }"],
            capture_output=True, text=True, timeout=60)
        for ln in (ps.stdout or '').splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if exclude_marker and exclude_marker in ln:
                continue
            out.append(ln)
    except Exception as e:  # pragma: no cover
        out.append('PROC-CHECK-FAILED: %s' % e)
    return out


def wait_for_clear(max_wait_s, poll_s=15):
    t0 = time.time()
    while True:
        busy = pcsx2_procs()
        if not busy:
            return time.time() - t0
        print('[wait] %.0fs 仍有 %d 个外部 pcsx2 实例, 等待中: %s'
              % (time.time() - t0, len(busy), busy[0][:160]), flush=True)
        if time.time() - t0 > max_wait_s:
            print('[wait] 超时 %.0fs, 仍有外部实例' % max_wait_s, flush=True)
            return -1.0
        time.sleep(poll_s)


class Contention(threading.Thread):
    """跑的过程中每 5 s 采一次: 有没有**别人的** pcsx2 实例在跑。"""

    def __init__(self, marker, path):
        super().__init__(daemon=True)
        self.marker = marker
        self.path = path
        self.stop_flag = False
        self.n_overlap = 0

    def run(self):
        with io.open(self.path, 'w', encoding='utf-8') as f:
            f.write('t_s,foreign_instances,foreign_pids\n')
            t0 = time.time()
            while not self.stop_flag:
                foreign = pcsx2_procs(exclude_marker=self.marker)
                if foreign:
                    self.n_overlap += 1
                pids = ';'.join(x.split('|', 1)[0] for x in foreign)
                f.write('%.1f,%d,%s\n' % (time.time() - t0, len(foreign), pids))
                f.flush()
                for _ in range(50):
                    if self.stop_flag:
                        return
                    time.sleep(0.1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True)
    ap.add_argument('--iso', required=True)
    ap.add_argument('--frames', type=int, default=32000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--nav', default='nav_play_v4.txt')
    ap.add_argument('--tag', default='')
    ap.add_argument('--wait-clear-s', type=int, default=2700)
    ap.add_argument('--perf', type=int, default=1)
    ap.add_argument('--force-contended', action='store_true')
    a = ap.parse_args()

    # ★ 必须 normpath: gsrunner 对 "C:\...\a/work/builds/x.iso" 这种**混合分隔符**路径
    #   会在加载 BIOS 之前直接退出 (exit=1, '=== run end, frames=0 ===', 见本目录
    #   证据 smoke_test_path.md)。全反斜杠绝对路径才正常。
    iso = os.path.normpath(a.iso)
    nav = os.path.normpath(a.nav if os.path.isabs(a.nav) else os.path.join(TOOLS, a.nav))
    for p in (iso, GS, nav):
        if not os.path.isfile(p):
            raise SystemExit('缺少文件: %s' % p)

    name = '%s_%s' % (a.arm, a.tag) if a.tag else a.arm
    out = os.path.join(ROOT, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    mc = os.path.join(out, 'mc')
    os.makedirs(mc)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))

    pre = pcsx2_procs()
    if pre:
        print('PRE-RESIDUAL (起跑前存在外部实例) -> 进入等待:')
        for p in pre:
            print('   ' + p)
    waited = wait_for_clear(a.wait_clear_s)

    args = [GS, '-grdumpdir', out, '-grmaxframes', str(a.frames),
            '-grsnap', str(a.snap), '-grinput', nav, '-grmemcards', mc,
            '-logfile', os.path.join(out, 'emulog.txt')]
    if a.perf:
        args.append('-perf')
    args += ['--', iso]
    cmdline = ' '.join(('"%s"' % x) if ' ' in x else x for x in args)

    if waited < 0 and not a.force_contended:
        lines = [
            'arm = %s' % name,
            'iso = %s' % iso,
            'nav = %s' % nav,
            'maxframes = %d' % a.frames,
            'snap = %d' % a.snap,
            'perf = %d' % (1 if a.perf else 0),
            'cmd = %s' % cmdline,
            'start = %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit = 9',
            'aborted = wait_timeout_no_clear_slot',
            'elapsed_s = 0.0',
            'pre_residual = %s' % (' | '.join(pre) if pre else 'none'),
            'waited_for_clear_s = %.0f' % waited,
            'foreign_overlap_during_run = not_run',
            'post_procs = not_run',
        ]
        with io.open(os.path.join(out, 'RUN.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print('\n'.join(lines))
        sys.exit(9)

    ct = Contention(out, os.path.join(out, 'contention.csv'))
    ct.start()

    t0 = time.time()
    with io.open(os.path.join(out, 'stdout.txt'), 'wb') as so:
        p = subprocess.Popen(args, cwd=os.path.dirname(GS), stdout=so,
                             stderr=subprocess.STDOUT)
        rc = p.wait()
    el = time.time() - t0
    ct.stop_flag = True
    ct.join(timeout=10)

    post = pcsx2_procs()
    post_str = 'none' if not post else ' | '.join(post)
    overlap = 'yes(%d samples)' % ct.n_overlap if ct.n_overlap else 'no'

    lines = [
        'arm = %s' % name,
        'iso = %s' % iso,
        'nav = %s' % nav,
        'maxframes = %d' % a.frames,
        'snap = %d' % a.snap,
        'perf = %d' % (1 if a.perf else 0),
        'cmd = %s' % cmdline,
        'start = %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t0)),
        'end   = %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t0 + el)),
        'exit = %d' % rc,
        'elapsed_s = %.1f' % el,
        'pre_residual = %s' % ('none' if not pre else ' | '.join(pre)),
        'waited_for_clear_s = %.0f' % waited,
        'foreign_overlap_during_run = %s' % overlap,
        'post_procs = %s' % post_str,
    ]
    with io.open(os.path.join(out, 'RUN.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    for ln in lines:
        print(ln)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
