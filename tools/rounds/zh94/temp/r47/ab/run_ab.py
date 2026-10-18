# -*- coding: utf-8 -*-
r"""run_ab.py — round47 实机 A/B 驱动: 修前 GR_ZH94 → 修后 GR_ZH96_fix, 严格串行。

· 用 tools/capture/run_opt.py 跑 (它每轮把 third_party/emu/run/memcards 的模板卡复位
  ⇒ 两轮引导时间线可比);
· 每轮跑完**等 pcsx2-gsrunner 进程消失** + 30s 复查, 才起下一轮 (绝不并发);
· 全程写日志 work/builds/GR_ZH94/temp/r47/ab/run_ab.log。
"""
import io
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
PY = sys.executable
LOG = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r47', 'ab', 'run_ab.log')
RUNOPT = os.path.join(REPO, 'tools', 'capture', 'run_opt.py')


def log(msg):
    line = '%s  %s' % (time.strftime('%H:%M:%S'), msg)
    print(line, flush=True)
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write(line + '\n')


def emu_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2-gsrunner.exe', '/NH'],
                         capture_output=True, text=True, errors='replace').stdout
    return [ln.split()[1] for ln in out.splitlines() if 'pcsx2-gsrunner' in ln]


def wait_no_emu(tag):
    for _ in range(180):
        if not emu_pids():
            break
        time.sleep(5)
    log('%s: 等仿真器退出后 pcsx2 pids=%s' % (tag, emu_pids()))
    time.sleep(30)
    log('%s: 30s 复查 pcsx2 pids=%s' % (tag, emu_pids()))


def run_round(tag, iso, name):
    env = dict(os.environ)
    env['GR_ISO'] = iso
    env.pop('GR_KEEP_MC', None)
    log('=== %s 开始: ISO=%s tag=%s nav=nav_r47.txt maxf=32000 snap=100' % (tag, iso, name))
    t0 = time.time()
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write('--- run_opt 输出开始 (%s) ---\n' % tag)
        f.flush()
        r = subprocess.run([PY, RUNOPT, name, 'nav_r47.txt', '32000', '100'],
                           cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT)
        f.write('--- run_opt 输出结束 (%s) rc=%s ---\n' % (tag, r.returncode))
    log('=== %s 结束: rc=%s 用时 %.0fs' % (tag, r.returncode, time.time() - t0))
    return r.returncode


def main():
    log('=== AB start (driver=python) ===  pre pcsx2 pids=%s' % emu_pids())
    rc1 = run_round('round1 修前 GR_ZH94', os.path.join(REPO, 'work', 'builds', 'GR_ZH94',
                                                        'GR_ZH94.iso'), 'r47before')
    wait_no_emu('round1')
    rc2 = run_round('round2 修后 GR_ZH96_fix', os.path.join(REPO, 'work', 'builds',
                                                            'GR_ZH96_fix', 'GR_ZH96_fix.iso'),
                    'r47after')
    wait_no_emu('round2')
    for d in (os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'dump_r47before'),
              os.path.join(REPO, 'work', 'builds', 'GR_ZH96_fix', 'temp', 'dump_r47after')):
        n = len([f for f in os.listdir(d) if f.startswith('snap_')]) if os.path.isdir(d) else -1
        log('dump %s  snaps=%d' % (d, n))
    log('=== AB done: rc1=%s rc2=%s ===' % (rc1, rc2))


if __name__ == '__main__':
    main()
