# -*- coding: utf-8 -*-
r"""analyze.py -- 把一次 gsrunner 手臂的产物折成可复算的数字。

输入: 一个 dump 目录 (含 RUN.txt / emulog.txt / grlog.txt / snap_f*.png)
输出: stdout 表格 + <dir>\ANALYSIS.json

指标 (全部可复算):
  1. frames        grlog.txt 里 "=== run end, frames=N ==="
  2. elapsed_s     RUN.txt 里的墙钟
  3. eff_fps       frames / elapsed_s            <- "整段平均帧率"
  4. tlb / trap / unmapped / pausing   emulog.txt 计数 (+ TLB 时间戳分布)
  5. 连续同画面最长段  snap_f*.png 按帧号排序后逐张 sha1, 找最长连续相同 run
  6. fps 时间线     相邻快照的**文件 mtime** 差 -> 局部帧率; 给出 min/p5/median/p95/max
                    和所有 "慢窗口" (单张快照耗时 > 阈值), 这是"掉到 2fps"的直接指纹
"""
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime


def parse_run(d):
    p = os.path.join(d, 'RUN.txt')
    out = {}
    if os.path.isfile(p):
        for ln in io.open(p, encoding='utf-8', errors='replace'):
            if '=' in ln:
                k, v = ln.split('=', 1)
                out[k.strip()] = v.strip()
    return out


def grlog_frames(d):
    p = os.path.join(d, 'grlog.txt')
    if not os.path.isfile(p):
        return None, None
    n = None
    with io.open(p, encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = re.search(r'=== run end, frames=(\d+) ===', ln)
            if m:
                n = int(m.group(1))
    return n, os.path.getsize(p)


def emulog_stats(d):
    p = os.path.join(d, 'emulog.txt')
    st = {'exists': os.path.isfile(p), 'bytes': 0, 'tlb': 0, 'tlb_ts': [],
          'trap': 0, 'unmapped': 0, 'pausing': 0, 'bios': None, 'iso': None,
          'crc': None, 'tlb_kinds': {}}
    if not st['exists']:
        return st
    st['bytes'] = os.path.getsize(p)
    ts_re = re.compile(r'^\[\s*([0-9.]+)\]\s*(.*)$')
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        m = ts_re.match(ln.rstrip('\r\n'))
        ts, body = (float(m.group(1)), m.group(2)) if m else (None, ln)
        if 'TLB Miss' in body:
            st['tlb'] += 1
            if ts is not None:
                st['tlb_ts'].append(round(ts, 3))
            mm = re.search(r'\[(load|store)\]', body)
            if mm:
                st['tlb_kinds'][mm.group(1)] = st['tlb_kinds'].get(mm.group(1), 0) + 1
        if 'Trap exception' in body:
            st['trap'] += 1
        if 'unmapped' in body.lower():
            st['unmapped'] += 1
        if 'Pausing' in body:
            st['pausing'] += 1
        if 'BIOS Found' in body:
            st['bios'] = body.strip()
        if 'isoFile open ok' in body:
            st['iso'] = body.split('isoFile open ok:')[-1].strip()
        if 'Game CRC' in body:
            st['crc'] = body.strip()
    return st


def snapshots(d):
    """返回 [(frame, path, sha1, size, mtime), ...] 按帧号升序。"""
    rx = re.compile(r'^snap_f(\d+)\.png$')
    items = []
    for fn in os.listdir(d):
        m = rx.match(fn)
        if not m:
            continue
        p = os.path.join(d, fn)
        h = hashlib.sha1()
        with open(p, 'rb') as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
        stt = os.stat(p)
        items.append((int(m.group(1)), p, h.hexdigest(),
                      stt.st_size, stt.st_mtime))
    items.sort(key=lambda x: x[0])
    return items


def same_runs(snaps, snap_interval, top=12):
    """连续同画面最长段 (帧数 = 张数 * snap_interval)。返回带帧区间的明细。"""
    if not snaps:
        return {}
    runs = []
    start = 0
    for i in range(1, len(snaps)):
        if snaps[i][2] != snaps[i - 1][2]:
            runs.append((start, i - 1))
            start = i
    runs.append((start, len(snaps) - 1))
    detail = []
    for (a, b) in runs:
        n = b - a + 1
        detail.append({'n': n, 'frames': n * snap_interval,
                       'f_from': snaps[a][0], 'f_to': snaps[b][0]})
    detail.sort(key=lambda x: -x['n'])
    distinct = len(set(s[2] for s in snaps))
    return {'n_snaps': len(snaps), 'distinct': distinct,
            'dedup_ratio': '%d/%d' % (distinct, len(snaps)),
            'longest_run_n': detail[0]['n'],
            'longest_run_frames': detail[0]['frames'],
            'top_runs': detail[:top],
            'top_runs_frames': [d['frames'] for d in detail[:top]]}


def fps_timeline(snaps, snap_interval, k=3.0, floor_ms=200.0):
    """用相邻快照的文件 mtime 差算局部帧率。
    "慢窗口" 阈值取 max(floor_ms, k * 中位 dt) —— 快照间隔 30 帧时中位 dt 本来就有
    0.5 s, 用绝对阈值会把每个窗口都判成慢。"""
    if len(snaps) < 3:
        return {}
    pts = []
    for i in range(1, len(snaps)):
        dt = snaps[i][4] - snaps[i - 1][4]
        if dt <= 0:
            continue
        pts.append((snaps[i][0], dt, snap_interval / dt))
    if not pts:
        return {}
    # 快照是异步队列(CPU 线程排队 -> GS 线程编码 PNG), 偶尔两张会在同一瞬间落盘
    # ⇒ dt≈0 ⇒ 局部 fps 假性爆表。先算中位 dt, 再把 dt < 0.2*中位 的对判为队列伪影剔除。
    med_all = sorted(p[1] for p in pts)[len(pts) // 2]
    valid = [p for p in pts if p[1] >= 0.2 * med_all]
    n_dropped = len(pts) - len(valid)
    pts = valid
    if not pts:
        return {}
    dts = sorted(p[1] for p in pts)
    fps = sorted(p[2] for p in pts)

    def pct(a, q):
        if not a:
            return 0.0
        i = min(len(a) - 1, max(0, int(round(q * (len(a) - 1)))))
        return a[i]

    med = pct(dts, .5)
    thr = max(floor_ms / 1000.0, k * med)
    slow = [{'frame': p[0], 'dt_s': round(p[1], 3), 'fps': round(p[2], 2)}
            for p in pts if p[1] >= thr]
    slow_sorted = sorted(slow, key=lambda x: -x['dt_s'])
    return {
        'n_pairs': len(pts),
        'n_queue_artifacts_dropped': n_dropped,
        'fps_min': round(fps[0], 2), 'fps_p5': round(pct(fps, .05), 2),
        'fps_median': round(pct(fps, .5), 2),
        'fps_p95': round(pct(fps, .95), 2), 'fps_max': round(fps[-1], 2),
        'dt_min_s': round(dts[0], 4), 'dt_median_s': round(pct(dts, .5), 4),
        'dt_max_s': round(dts[-1], 4),
        'slow_threshold_s': round(thr, 3),
        'n_slow_windows': len(slow),
        'slowest12': slow_sorted[:12],
    }


def hwstats(d):
    """-perf 时 gsrunner 退出前打印的 @HWSTAT@ 单帧时间统计 (独立于快照 mtime 的读数)。"""
    p = os.path.join(d, 'stdout.txt')
    if not os.path.isfile(p):
        return {}
    out = {}
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        if '@HWSTAT@' in ln:
            body = ln.split('@HWSTAT@', 1)[1].strip()
            if ':' in body:
                k, v = body.split(':', 1)
                out[k.strip()] = v.strip()
    return out


def main():
    d = os.path.abspath(sys.argv[1])
    snap_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    run = parse_run(d)
    frames, grlog_bytes = grlog_frames(d)
    el = float(run.get('elapsed_s', '0') or 0)
    e = emulog_stats(d)
    snaps = snapshots(d)
    rep = {
        'dir': d,
        'arm': run.get('arm'),
        'iso': run.get('iso'),
        'nav': run.get('nav'),
        'exit': run.get('exit'),
        'elapsed_s': el,
        'grlog_bytes': grlog_bytes,
        'frames': frames,
        'eff_fps': round(frames / el, 2) if (frames and el) else None,
        'snap_interval': snap_interval,
        'emulog': e,
        'hwstats': hwstats(d),
        'same_frames': same_runs(snaps, snap_interval),
        'fps_timeline': fps_timeline(snaps, snap_interval),
    }
    with io.open(os.path.join(d, 'ANALYSIS.json'), 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    print('=== %s ===' % (run.get('arm') or d))
    print('  iso            = %s' % run.get('iso'))
    print('  exit           = %s   elapsed = %s s' % (run.get('exit'), run.get('elapsed_s')))
    print('  frames(run end)= %s   eff_fps = %s' % (frames, rep['eff_fps']))
    print('  TLB Miss       = %d %s   kinds=%s' % (e['tlb'], e['tlb_ts'][:5], e['tlb_kinds']))
    print('  Trap=%d unmapped=%d Pausing=%d' % (e['trap'], e['unmapped'], e['pausing']))
    print('  BIOS           = %s' % e['bios'])
    sf = rep['same_frames']
    print('  snapshots      = %s  distinct=%s  longest_same_run=%s frames' %
          (sf.get('n_snaps'), sf.get('dedup_ratio'), sf.get('longest_run_frames')))
    for r in sf.get('top_runs', [])[:6]:
        print('     same-screen run: %5d frames  f%d..f%d' %
              (r['frames'], r['f_from'], r['f_to']))
    tl = rep['fps_timeline']
    if tl:
        print('  fps local      = min %.2f  p5 %.2f  med %.2f  p95 %.2f  max %.2f' %
              (tl['fps_min'], tl['fps_p5'], tl['fps_median'], tl['fps_p95'], tl['fps_max']))
        print('  slow windows   = %d (dt >= %.3f s); slowest: %s' %
              (tl['n_slow_windows'], tl['slow_threshold_s'],
               [(s['frame'], s['fps']) for s in tl['slowest12'][:6]]))
    hw = rep['hwstats']
    if hw:
        print('  @HWSTAT@       = min %s | avg %s | MAX %s' %
              (hw.get('Minimum Frame Time'), hw.get('Average Frame Time'),
               hw.get('Maximum Frame Time')))
        print('                   CPU thread %s | GS thread %s | GPU %s' %
              (hw.get('CPU Thread Usage'), hw.get('GS Thread Usage'),
               hw.get('GPU Usage')))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
