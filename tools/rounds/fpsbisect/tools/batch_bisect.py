# -*- coding: utf-8 -*-
r"""batch_bisect.py -- 串行跑一批手臂（绝不并发），每臂跑完立刻抽数并清理大体积中间产物。

用法:
  python work\builds\GR_FPSBISECT\tools\batch_bisect.py --plan work\builds\GR_FPSBISECT\plan.json \
      [--only A] [--on-timeout abort|next] [--deadline-s 12600]

每臂调用 run_arm_bisect.py（与 GR_FPS\tools\run_arm.py 逐字同配方，只换 ROOT 与超时策略）。
跑完一臂后:
  * 抽数 -> work\builds\GR_FPSBISECT\quick\<arm>.json   (frames / elapsed / eff_fps / @HWSTAT@ / TLB / 污染)
  * 删掉 gsrunner 的默认 needle 大转储 eeram_*.bin / iopram_*.bin（与本结论无关，且可随时再生）
  * 记一条 work\builds\GR_FPSBISECT\batch_log.txt
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
BIS = os.path.join(REPO, 'work', 'builds', 'GR_FPSBISECT')
PY = sys.executable
RUNNER = os.path.join(BIS, 'tools', 'run_arm_bisect.py')


def log(msg):
    line = '[%s] %s' % (time.strftime('%H:%M:%S'), msg)
    print(line, flush=True)
    with io.open(os.path.join(BIS, 'batch_log.txt'), 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def free_gb():
    try:
        import ctypes
        fb = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p('C:\\'), None, None, ctypes.byref(fb))
        return fb.value / (1024.0 ** 3)
    except Exception:
        return -1.0


def parse_run(d):
    out = {}
    p = os.path.join(d, 'RUN.txt')
    if os.path.isfile(p):
        for ln in io.open(p, encoding='utf-8', errors='replace'):
            if '=' in ln:
                k, v = ln.split('=', 1)
                out[k.strip()] = v.strip()
    return out


def grlog_frames(d):
    p = os.path.join(d, 'grlog.txt')
    n = None
    if os.path.isfile(p):
        for ln in io.open(p, encoding='utf-8', errors='replace'):
            m = re.search(r'=== run end, frames=(\d+) ===', ln)
            if m:
                n = int(m.group(1))
    return n


def emulog_quick(d):
    """从 emulog.txt 抽: 最后一个 HW STATISTICS 块的 @HWSTAT@ 行 + 降级指纹。"""
    p = os.path.join(d, 'emulog.txt')
    st = {'tlb': 0, 'trap': 0, 'unmapped': 0, 'pausing': 0, 'bios': None,
          'iso': None, 'crc': None, 'hwstats': {}, 'bytes': 0}
    if not os.path.isfile(p):
        return st
    st['bytes'] = os.path.getsize(p)
    blocks = []
    cur = None
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        b = ln.rstrip('\r\n')
        if 'HW STATISTICS FOR' in b:
            cur = {}
            blocks.append(cur)
            continue
        if '@HWSTAT@' in b:
            body = b.split('@HWSTAT@', 1)[1].strip()
            if ':' in body and cur is not None:
                k, v = body.split(':', 1)
                cur[k.strip()] = v.strip()
        if 'TLB Miss' in b:
            st['tlb'] += 1
        if 'Trap exception' in b:
            st['trap'] += 1
        if 'unmapped' in b.lower():
            st['unmapped'] += 1
        if 'Pausing' in b:
            st['pausing'] += 1
        if 'BIOS Found' in b:
            st['bios'] = b.strip()
        if 'isoFile open ok' in b:
            st['iso'] = b.split('isoFile open ok:')[-1].strip()
        if 'Game CRC' in b:
            st['crc'] = b.strip()
    st['n_hwstat_blocks'] = len(blocks)
    if blocks:
        st['hwstats'] = blocks[-1]
    return st


def cleanup_big(d):
    """删掉 gsrunner 默认 needle 的 EE/IOP RAM 转储（与本结论无关、可再生）。

    实测文件名（2026-10-15）= `<needle>_f<frame>_eeram.bin` / `..._iopram.bin`，
    每个 32 MB / 2 MB，一条 32000 帧的臂约 12 组 ≈ 400 MB。
    前一版 glob 写的 `eeram_*.bin` **匹配不到**（前缀是 needle 名，不是 eeram），已改正。
    """
    n = 0
    by = 0
    for pat in ('*_eeram.bin', '*_iopram.bin', 'eeram_*.bin', 'iopram_*.bin'):
        for f in glob.glob(os.path.join(d, pat)):
            try:
                by += os.path.getsize(f)
                os.remove(f)
                n += 1
            except OSError:
                pass
    return n, by


def dir_bytes(d):
    tot = 0
    for root, _dirs, files in os.walk(d):
        for fn in files:
            try:
                tot += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--only', default='')
    ap.add_argument('--on-timeout', default='abort', choices=['abort', 'next'])
    ap.add_argument('--deadline-s', type=int, default=0)
    ap.add_argument('--tag', default='fpsbisect')
    ap.add_argument('--wait-clear-s', type=int, default=2400)
    a = ap.parse_args()

    with io.open(a.plan, encoding='utf-8') as f:
        plan = json.load(f)

    t_start = time.time()
    qdir = os.path.join(BIS, 'quick')
    if not os.path.isdir(qdir):
        os.makedirs(qdir)

    log('=== batch start  free=%.2f GB  plan=%s  only=%r  deadline=%ds ==='
        % (free_gb(), os.path.basename(a.plan), a.only, a.deadline_s))

    aborted = False
    for item in plan:
        b = item['batch']
        arm = item['arm']
        iso = item['iso']
        iso = os.path.normpath(iso if os.path.isabs(iso) else os.path.join(REPO, iso))
        if not os.path.isfile(iso):
            log('MISSING ISO %s -> skip %s' % (iso, arm))
            continue
        if a.only and b != a.only:
            continue
        if aborted:
            log('SKIP %s (batch aborted earlier)' % arm)
            continue
        if a.deadline_s and (time.time() - t_start) > a.deadline_s:
            log('DEADLINE %.0fs reached -> stop; %s not run' % (a.deadline_s, arm))
            break

        name = '%s_%s' % (arm, a.tag)
        out = os.path.join(BIS, 'out', name)
        cmd = [PY, RUNNER, '--arm', arm, '--iso', iso, '--frames', '32000',
               '--snap', '60', '--perf', '1', '--nav', 'nav_play_v4.txt',
               '--tag', a.tag, '--wait-clear-s', str(a.wait_clear_s)]
        log('RUN  %-18s batch=%s  iso=%s  free=%.2f GB' % (arm, b, os.path.basename(iso), free_gb()))
        t0 = time.time()
        with io.open(os.path.join(qdir, name + '.runlog.txt'), 'w', encoding='utf-8') as lf:
            rc = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT)
        dt = time.time() - t0

        run = parse_run(out)
        e = emulog_quick(out) if rc == 0 else {'note': 'no emulog (rc=%d)' % rc}
        frames = grlog_frames(out)
        el = float(run.get('elapsed_s', '0') or 0)
        size_before = dir_bytes(out)
        ndel, bydel = cleanup_big(out)
        rec = {
            'arm': arm, 'batch': b, 'name': name, 'iso': iso, 'rc': rc,
            'wall_s': round(dt, 1),
            'elapsed_s': el,
            'frames': frames,
            'eff_fps': round(frames / el, 2) if (frames and el > 0) else None,
            'run': run,
            'emulog': e,
            'out_bytes': size_before,
            'cleaned_files': ndel, 'cleaned_bytes': bydel,
            'free_gb_after': round(free_gb(), 2),
        }
        with io.open(os.path.join(qdir, name + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)

        hw = e.get('hwstats', {}) if isinstance(e, dict) else {}
        log('DONE %-18s rc=%d wall=%.0fs frames=%s elapsed=%.1fs eff_fps=%s '
            'cpu_thread=%s avg_frame=%s max_frame=%s tlb=%s overlap=%s freed=%.1f MB'
            % (arm, rc, dt, frames, el, rec['eff_fps'],
               hw.get('Average CPU Thread Time'), hw.get('Average Frame Time'),
               hw.get('Maximum Frame Time'), e.get('tlb') if isinstance(e, dict) else '?',
               run.get('foreign_overlap_during_run'), bydel / 1048576.0))

        if rc == 9:
            log('WAIT-TIMEOUT (别人长期占用模拟器) -> on-timeout=%s' % a.on_timeout)
            if a.on_timeout == 'abort':
                aborted = True

    log('=== batch end  free=%.2f GB  total=%.0fs ===' % (free_gb(), time.time() - t_start))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
