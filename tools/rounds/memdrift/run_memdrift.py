# -*- coding: utf-8 -*-
r"""run_memdrift.py — 汉化盘 / 英文原盘 的长时间游玩回放 + 内存漂移取证 (只读 ISO)

取证手段 (全部是研究构筑 pcsx2-gsrunner 的既有开关, 见 GRResearch.cpp)
--------------------------------------------------------------------
  -grperiodram N    每 N 帧转存**全部 EE RAM (32 MB) + IOP RAM (2 MB)**
                    → period_f%08u_eeram.bin / _iopram.bin  (帧号在文件名里)
  -grmemwatch A S 1 每帧往 memwatch.bin 追加 [u32 frame][u32 addr][u32 size][S 字节]
                    (共享打开 + 每帧 fflush ⇒ 外部可实时 tail; 这里只用来做"帧号心跳")
  -grpcsample 1     每 4 帧往 pcsample.txt 写 "<frame> <cpuRegs.pc>"
                    ★ 这是**卡死判定**的关键: 画面静止 = EE 卡在极少数几个 PC 上,
                      正常游玩时 PC 分布很宽。
  -grsnap N         每 N 帧截图 (PNG) → 用"连续 N 张逐字节相同"判画面静止
  -grinput <file>   确定性按键时间线 (frame button tap|hold|release)

纪律
----
  · 只读 ISO; 所有产物写 --out
  · **一次只有一个模拟器实例**: 启动前等 pcsx2-gsrunner 清零
  · 日志被独占: 进程退出后才读 emulog / pcsample / grlog
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
BIOS_USER = 'SCPH-90006_BIOS_VX_HK_2.20.bin'


def proc_count():
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              '@(Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue).Count'],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return int(out) if out.isdigit() else 0
    except Exception:                                                  # noqa: BLE001
        return -1


def wait_clear(max_s=1800):
    t0 = time.time()
    while True:
        n = proc_count()
        if n == 0:
            return time.time() - t0
        if time.time() - t0 > max_s:
            raise SystemExit('!! 等 %.0f s 仍有 %d 个 pcsx2-gsrunner 在跑 —— 不抢占, 退出'
                             % (max_s, n))
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True, help='如 zh113b_long / en_orig_long')
    ap.add_argument('--iso', required=True)
    ap.add_argument('--input', required=True, help='-grinput 时间线')
    ap.add_argument('--frames', type=int, default=80000)
    ap.add_argument('--periodram', type=int, default=2500)
    ap.add_argument('--snap', type=int, default=300)
    ap.add_argument('--pcsample', type=int, default=1)
    ap.add_argument('--bios', default=BIOS_USER,
                    help='BIOS 文件名; 传 "" 用模拟器默认(Europe v01.60)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--state', default=None,
                    help='★ .p2s 存档: 直接在关卡内起跑 (VMManager 的 save_state)')
    ap.add_argument('--watch', default=None,
                    help='-grwatch <addr> <size>: 逐块记录"谁改了这个区间" (开启 trace-all-blocks, 慢)')
    ap.add_argument('--extra', default=None, help='额外原样附加的 -gr* 参数 (空格分隔)')
    ap.add_argument('--memwatch', action='append', default=None,
                    help='-grmemwatch 区域 "<addr> <size> <interval>", 可重复; '
                         '缺省 = 0x013379D0 4 1 (帧号心跳)')
    a = ap.parse_args()
    mws = a.memwatch or ['0x013379D0 4 1']

    out = os.path.abspath(a.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, 'mc'))
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(out, 'mc', f))

    print('等模拟器空闲 ...', flush=True)
    w = wait_clear()
    print('  空闲 (等了 %.0f s)' % w, flush=True)
    time.sleep(1.0)

    args = [GS, '-grdumpdir', out,
            '-grmaxframes', str(a.frames),
            '-grsnap', str(a.snap),
            '-grperiodram', str(a.periodram),
            '-grscanframes', '100000',
            '-grinput', os.path.abspath(a.input),
            '-grmemcards', os.path.join(out, 'mc'),
            '-logfile', os.path.join(out, 'emulog.txt')]
    for m in mws:
        args += ['-grmemwatch'] + m.split()
    if a.pcsample:
        args += ['-grpcsample', '1']
    if a.state:
        args += ['-grstate', os.path.abspath(a.state)]
    if a.watch:
        args += ['-grwatch'] + a.watch.split()
    if a.extra:
        args += a.extra.split()
    if a.bios:
        args += ['-grbiosname', a.bios]
    args += ['--', os.path.abspath(a.iso)]

    with open(os.path.join(out, 'RUN.txt'), 'w', encoding='utf-8') as fh:
        fh.write('tag = %s\niso = %s\ninput = %s\nframes = %d\nperiodram = %d\nsnap = %d\n'
                 'bios = %s\npre_residual = none (waited %.0f s)\nstart = %s\ncmd = %s\n'
                 % (a.tag, a.iso, a.input, a.frames, a.periodram, a.snap, a.bios, w,
                    time.strftime('%Y-%m-%d %H:%M:%S'), ' '.join(args)))
    print('cmd = %s' % ' '.join(args), flush=True)

    t0 = time.time()
    with open(os.path.join(out, 'stdout.txt'), 'wb') as so:
        p = subprocess.Popen(args, cwd=os.path.dirname(GS), stdout=so, stderr=subprocess.STDOUT)
    print('pid = %d' % p.pid, flush=True)

    mw = os.path.join(out, 'memwatch.bin')
    stride = 12 + 4                                  # 缺省单区域 (4 B) ⇒ 12+4
    try:
        stride = sum(12 + int(m.split()[1]) for m in mws)
    except Exception:                                                # noqa: BLE001
        pass
    last_report, stall_since, last_frame, frozen = 0.0, None, None, False
    hang = None
    try:
        while p.poll() is None:
            time.sleep(5.0)
            fr = None
            try:
                sz = os.path.getsize(mw)
                n = sz // stride
                if n:
                    with open(mw, 'rb') as f:
                        f.seek((n - 1) * stride)
                        fr = int.from_bytes(f.read(4), 'little')
            except OSError:
                pass
            now = time.time() - t0
            if fr is not None and fr != last_frame:
                last_frame, stall_since = fr, now
            # 心跳: 每 90 s 报一次
            if now - last_report >= 90:
                last_report = now
                eff = (last_frame or 0) / max(now, 1e-9)
                print('  [t=%6.0fs] frame=%-7s (%.1f fps 均) pid存活=%s'
                      % (now, last_frame, eff, p.poll() is None), flush=True)
            # ★ 注意: 本作卡死时 **帧号仍会推进** (EE 在异常循环里照样耗周期),
            #   所以帧号停住**不是**卡死判据 —— 判据在 pcsample/截图 (跑完离线判)。
    finally:
        if p.poll() is None:
            print('  [收尾] 未到 -grmaxframes, 主动 terminate ...', flush=True)
            p.terminate()
            try:
                p.wait(timeout=180)
            except Exception:                                        # noqa: BLE001
                p.kill()
                p.wait(timeout=60)
    el = time.time() - t0
    rc = p.returncode

    # ---- 进程已退出, 现在才可以读日志 ----
    res = dict(tag=a.tag, iso=a.iso, input=a.input, exit=rc, elapsed_s=round(el, 1),
               maxframes=a.frames, periodram=a.periodram, snap=a.snap, bios=a.bios,
               cmd=args, out=out)

    def readtext(name):
        pth = os.path.join(out, name)
        if not os.path.isfile(pth):
            return None
        with open(pth, encoding='utf-8', errors='replace') as fh:
            return fh.read()

    el_ = readtext('emulog.txt') or ''
    res['emulog_bytes'] = len(el_)
    res['tlb_miss'] = el_.count('TLB Miss')
    res['trap'] = el_.count('Trap exception')
    res['buserr'] = el_.count('Bus Error')
    res['unmapped'] = el_.count('unmapped')
    # BIOS / 游戏识别
    for ln in el_.splitlines():
        if 'BIOS Found' in ln or 'BIOS Version' in ln:
            res['bios_found'] = ln.strip()
            break
    for ln in el_.splitlines():
        if 'Game CRC' in ln:
            res['crc'] = ln.strip()
            break
    # TLB miss 的 pc/addr 直方图
    hist = {}
    for ln in el_.splitlines():
        if 'TLB Miss' in ln:
            key = ln.split('] ', 1)[-1].strip()
            hist[key] = hist.get(key, 0) + 1
    res['tlb_hist'] = hist
    # 帧数
    for ln in el_.splitlines():
        if '=== run end, frames=' in ln:
            res['frames_run'] = int(ln.rsplit('frames=', 1)[1].split()[0].rstrip('='))
    res['gr_tail'] = [x for x in el_.splitlines() if x.startswith('[ ') and 'GR: ' in x][-6:]

    # pcsample 分析: 尾部 PC 分布 = 卡死判定
    ps = os.path.join(out, 'pcsample.txt')
    if os.path.isfile(ps):
        rows = []
        with open(ps, encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                q = ln.split()
                if len(q) == 2:
                    rows.append((int(q[0]), q[1].lower()))
        res['pcsample_lines'] = len(rows)
        res['pcsample_frames'] = '0..%d' % rows[-1][0] if rows else None
        if rows:
            # 全段 vs 最后 5% 的 distinct PC
            tail = rows[int(len(rows) * 0.95):]
            res['pc_distinct_all'] = len({r[1] for r in rows})
            res['pc_distinct_tail5pct'] = len({r[1] for r in tail})
            h = {}
            for (f, pc) in tail:
                h[pc] = h.get(pc, 0) + 1
            res['pc_tail_top'] = sorted(h.items(), key=lambda x: -x[1])[:12]
            # 最长"连续同一 PC"与"连续同 2 PC 集合"的游程
            best, cur = 1, 1
            for i in range(1, len(rows)):
                if rows[i][1] == rows[i - 1][1]:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 1
            res['pc_same_run_max'] = best
            best2, cur2, win = 1, 1, [rows[0][1]]
            for i in range(1, len(rows)):
                win.append(rows[i][1])
                if len(win) > 4:
                    win.pop(0)
                if len(set(win)) <= 2:
                    cur2 += 1
                    best2 = max(best2, cur2)
                else:
                    cur2, win = 1, [rows[i][1]]
            res['pc_two_pc_run_max'] = best2

    # 截图: 找最长的"逐字节相同"连续段 (画面静止)
    snaps = sorted(x for x in os.listdir(out) if x.startswith('snap_f') and x.endswith('.png'))
    res['snaps'] = len(snaps)
    if snaps:
        def keyf(s):
            return int(s[6:14])
        snaps.sort(key=keyf)
        hs, runs, cur, prev, start = [], [], 1, None, None
        import hashlib
        for s in snaps:
            with open(os.path.join(out, s), 'rb') as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            hs.append((keyf(s), h))
            if prev is not None and h == prev:
                cur += 1
            else:
                if cur > 1:
                    runs.append((cur, start, lastf))
                cur, start = 1, keyf(s)
            prev, lastf = h, keyf(s)
        if cur > 1:
            runs.append((cur, start, lastf))
        runs.sort(key=lambda x: -x[0])
        res['snap_distinct'] = len({h for (_f, h) in hs})
        res['snap_frozen_runs'] = [dict(n=n, f_from=f0, f_to=f1) for (n, f0, f1) in runs[:6]]

    with open(os.path.join(out, 'RESULT.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(out, 'RUN.txt'), 'a', encoding='utf-8') as fh:
        fh.write('end   = %s\nexit = %s\nelapsed_s = %.1f\n'
                 % (time.strftime('%Y-%m-%d %H:%M:%S'), rc, el))
    print('\n' + '=' * 74)
    print('tag=%s exit=%s 耗时=%.0f s (%.1f fps 均)' % (a.tag, rc, el, (res.get('frames_run') or 0) / max(el, 1e-9)))
    print('frames_run=%s  TLB Miss=%s  Trap=%s  BusErr=%s' % (res.get('frames_run'), res['tlb_miss'], res['trap'], res['buserr']))
    if res.get('tlb_hist'):
        print('TLB 直方图: %s' % json.dumps(res['tlb_hist'], ensure_ascii=False))
    if 'pc_distinct_tail5pct' in res:
        print('PC: 全段 distinct=%d, 尾 5%% distinct=%d, 最长同PC游程=%d, 最长≤2PC游程=%d'
              % (res['pc_distinct_all'], res['pc_distinct_tail5pct'],
                 res['pc_same_run_max'], res['pc_two_pc_run_max']))
        print('尾部热点 PC: %s' % res['pc_tail_top'])
    print('截图 %d 张, distinct=%s, 最长冻结段=%s'
          % (res.get('snaps', 0), res.get('snap_distinct'), res.get('snap_frozen_runs')))
    print('结果 = %s' % os.path.join(out, 'RESULT.json'))
    print('=' * 74, flush=True)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
