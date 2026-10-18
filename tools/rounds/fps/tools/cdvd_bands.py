# -*- coding: utf-8 -*-
r"""cdvd_bands.py -- 比较两臂的 CDVD 读盘行为 (帧号 -> LBA 已在 cdvd.log 里)。

cdvd.log 每行 = "<frame> <lba>" (CDVD 读钩子, 见 GRResearch.cpp InstallCdvdHook)。
据此算: 每个阶段的读次数 / 总 LBA 跳距(|ΔLBA|, 模拟光驱寻道的代理量) /
        平均跳距 / 最大跳距。用来判定"汉化盘是不是让游戏读得更多更远"
        —— 这是"额外 CPU 时间来自读盘等待"这一假说的直接判据。
"""
import io
import json
import os
import sys

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


def load(d):
    out = []
    p = os.path.join(d, 'cdvd.log')
    if not os.path.isfile(p):
        return out
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                out.append((int(parts[0]), int(parts[1])))
            except ValueError:
                pass
    return out


def main():
    rep = {}
    for d in sys.argv[1:]:
        d = os.path.abspath(d)
        r = load(d)
        name = os.path.basename(d)
        rows = []
        for (bn, f0, f1) in BANDS:
            sel = [x for x in r if f0 <= x[0] <= f1]
            # 跳距: 该阶段内**实际发生**的连续读之间的 |ΔLBA|
            jumps = []
            for i in range(1, len(sel)):
                jumps.append(abs(sel[i][1] - sel[i - 1][1]))
            rows.append({
                'band': bn, 'reads': len(sel),
                'lba_min': min([x[1] for x in sel], default=None),
                'lba_max': max([x[1] for x in sel], default=None),
                'jump_sum': sum(jumps),
                'jump_avg': round(sum(jumps) / len(jumps), 1) if jumps else None,
                'jump_max': max(jumps) if jumps else None,
            })
        rep[name] = {'reads_total': len(r), 'bands': rows,
                     'lba_first': r[0][1] if r else None,
                     'lba_last': r[-1][1] if r else None}
        print('=== %s ===  reads_total=%d  first_lba=%s last_lba=%s'
              % (name, len(r), rep[name]['lba_first'], rep[name]['lba_last']))
        print('  %-22s %8s %10s %12s %10s %9s' %
              ('band', 'reads', 'lba_min', 'lba_max', 'jump_sum', 'jump_avg'))
        for row in rows:
            print('  %-22s %8d %10s %12s %12s %9s' %
                  (row['band'], row['reads'], row['lba_min'], row['lba_max'],
                   row['jump_sum'], row['jump_avg']))
        print('')

    out = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), '..', 'CDVD_BANDS.json')
    with io.open(os.path.abspath(out), 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('wrote %s' % os.path.abspath(out))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
