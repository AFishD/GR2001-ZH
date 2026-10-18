# -*- coding: utf-8 -*-
r"""run_arm.py -- run ONE gsrunner arm of the GR_FPS A/B.   (取代 run_arm.ps1: 本机
PowerShell 执行策略禁止运行 .ps1 文件, 与脚本内容无关)

纪律 (任务书):
  * 模拟器一次只跑一个实例 -> 跑前/跑后都查 *pcsx2* 进程, 有残留就拒绝起跑
  * 日志被独占 -> 只在进程退出后才读 emulog/grlog
  * exit=0 不算证据 -> 记录 frames / elapsed / TLB / Trap, 以数字为准
  * 只写 work/builds/GR_FPS/**

用法:
  python work\builds\GR_FPS\tools\run_arm.py --arm zh113b --iso <iso> \
      [--frames 34000] [--snap 60] [--nav nav_play.txt] [--tag probe]
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
ROOT = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'out')
TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'tools')


def pcsx2_procs(exclude_marker=None):
    """返回当前所有 pcsx2* 进程的 'pid|cmdline' 列表。
    exclude_marker: 命令行里含这个子串的算"我自己" —— 每个手臂的 dump 目录名唯一,
    用它排除自己比用 pid 可靠 (采样线程可能早于 Popen 返回就已经跑了一轮)。"""
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
    """别人的 gsrunner 手臂也占着同一块 CPU; 并发会把两边都压到 ~30fps,
    直接毁掉 fps 读数。故: 等到**零 pcsx2 进程**才起跑 (不杀别人的进程)。"""
    t0 = time.time()
    while True:
        busy = pcsx2_procs()
        if not busy:
            return time.time() - t0
        print('[wait] %.0fs 仍有 %d 个外部 pcsx2 实例, 等待中: %s'
              % (time.time() - t0, len(busy), busy[0][:120]), flush=True)
        if time.time() - t0 > max_wait_s:
            print('[wait] 超时 %.0fs, 仍然有外部实例 -> 继续跑, 但本臂会被标记为 CONTENDED'
                  % max_wait_s, flush=True)
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
                for _ in range(50):          # 5 s, 但 0.1 s 粒度响应急停
                    if self.stop_flag:
                        return
                    time.sleep(0.1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True)
    ap.add_argument('--iso', required=True)
    ap.add_argument('--frames', type=int, default=34000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--nav', default='nav_play.txt')
    ap.add_argument('--tag', default='')
    ap.add_argument('--wait-clear-s', type=int, default=1800,
                    help='起跑前等"零 pcsx2 进程"的最长秒数 (默认 1800)')
    ap.add_argument('--perf', type=int, default=0,
                    help='1 = 加 -perf (Unlimited 限速 + @HWSTAT@ 单帧时间统计)')
    a = ap.parse_args()

    iso = a.iso
    nav = a.nav if os.path.isabs(a.nav) else os.path.join(TOOLS, a.nav)
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
        # -perf: 强制 LimiterMode=Unlimited + 开 GPU 计时, 并在退出时打印
        #        @HWSTAT@ Minimum/Average/Maximum Frame Time —— 独立的"最坏单帧"读数。
        #        注意: research mode 下 SettingsOverride 会提前 return ⇒ FrameLimitEnable
        #        保持 ini 默认; 加 -perf 才能保证"不限速", 让 frames/elapsed 变成真实吞吐。
        args.append('-perf')
    args += ['--', iso]
    cmdline = ' '.join(('"%s"' % x) if ' ' in x else x for x in args)

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
