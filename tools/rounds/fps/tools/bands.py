# -*- coding: utf-8 -*-
r"""bands.py -- 按"游戏阶段"把一次手臂的墙钟拆开, 定位汉化盘的额外耗时落在哪一段。

输入: dump 目录 (须有 snap_f*.png 与 RUN.txt)
输出: stdout 表 + <dir>\BANDS.json

原理: 每张快照 PNG 的文件 mtime = 该帧被写出的墙钟时刻 ⇒
      band 内 fps = (帧差) / (mtime 差)。同一段导航在两臂里帧号相同, 所以可以直接对表。
"""
import io
import json
import os
import re
import sys
import time

RX = re.compile(r'^snap_f(\d+)\.png$')

BANDS = [
    ('A_boot_logo', 0, 2500),
    ('B_file_select', 2500, 3500),
    ('C_main_menu_campaign', 3500, 7000),
    ('D_briefing_kit_load', 7000, 10600),
    ('E_inlevel_shoot', 10600, 15500),
    ('F_pause_save_load', 15500, 23200),
    ('G_squadkey_sweep', 23200, 30500),
    ('H_final_play', 30500, 32001),
]


def main():
    d = os.path.abspath(sys.argv[1])
    snaps = []
    for fn in os.listdir(d):
        m = RX.match(fn)
        if m:
            p = os.path.join(d, fn)
            snaps.append((int(m.group(1)), os.stat(p).st_mtime))
    snaps.sort()
    if not snaps:
        raise SystemExit('no snapshots in %s' % d)

    run = {}
    rp = os.path.join(d, 'RUN.txt')
    if os.path.isfile(rp):
        for ln in io.open(rp, encoding='utf-8', errors='replace'):
            if '=' in ln:
                k, v = ln.split('=', 1)
                run[k.strip()] = v.strip()

    out = {'dir': d, 'run': run, 'bands': []}
    print('=== %s ===' % d)
    print('  exit=%s elapsed=%s frames=%s' % (run.get('exit'), run.get('elapsed_s'), run.get('maxframes')))
    print('  %-22s %7s %7s %9s %9s' % ('band', 'f_from', 'f_to', 'span_s', 'fps'))
    for (name, f0, f1) in BANDS:
        sel = [s for s in snaps if f0 <= s[0] <= f1]
        if len(sel) < 2:
            print('  %-22s %7d %7d %9s %9s' % (name, f0, f1, '-', '-'))
            continue
        frames = sel[-1][0] - sel[0][0]
        span = sel[-1][1] - sel[0][1]
        fps = frames / span if span > 0 else None
        out['bands'].append({'band': name, 'f_from': sel[0][0], 'f_to': sel[-1][0],
                             'frames': frames, 'span_s': round(span, 3),
                             'fps': round(fps, 2) if fps else None})
        print('  %-22s %7d %7d %9.2f %9.2f' % (name, sel[0][0], sel[-1][0], span, fps))

    # 累计: 到每个 band 末尾的墙钟
    t0 = snaps[0][1]
    print('  --- cumulative wall clock from first snapshot (f=%d) ---' % snaps[0][0])
    for (name, f0, f1) in BANDS:
        sel = [s for s in snaps if s[0] <= f1]
        if sel:
            print('    %-22s @f%-6d t=+%.1f s' % (name, sel[-1][0], sel[-1][1] - t0))

    with io.open(os.path.join(d, 'BANDS.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
