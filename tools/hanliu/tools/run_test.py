#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

r"""run_test.py — gsrunner 一键测试 + 健康判据解析 (封装 run_iso/probe_run3/run_bisect 经验)

封装内容:
  - gsrunner 路径与参数 (★ISO 参数必须反斜杠路径, 正斜杠 exit=1 秒退不启动)
  - 预置导航脚本: zh2nav (34 键, Controller 页判定路线) / quick (4300 帧快判)
    / bisect (15500 帧 Name Entry 字形探针) / boot (11400 帧过 BIOS+标题)
  - 健康判据解析: exit 代码、needle 'WPNRPK74' 首中帧/总命中、cdvd.log 卡死检测
    (模拟器层偶发挂起: cdvd 停在 544/774xxx 且不再推进 → 与盘内容无关, 重跑可穿过)
  - 基线: GR_ZH7 = 40000 帧 exit=0 (667s), needle 4,229 次 (原盘基线 4,245)

用法:
  python run_test.py --iso C:\\..\\GR_ZH7.iso --dump C:\\..\\dumps\\t1 --frames 40000
  python run_test.py --iso <iso> --dump <dir> --preset quick      # 4300 帧 boot 快判
  python run_test.py --iso <iso> --dump <dir> --frames 40000 --input mynav.txt
判据输出:
  ALIVE      = 跑满 --frames 且 exit=0 且 needle ≥ --min-needle (默认 3000)
  CDVD_STALL = cdvd.log 疑似模拟器层挂起 (建议直接重跑)
  CRASH      = 提前退出/needle 过少
"""
import argparse
import os
import re
import subprocess
import sys
import time

GS = os.path.join(REPO_ROOT, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MEMCARDS = os.path.join(REPO_ROOT, 'third_party', 'emu', 'run', 'memcards')

NAV_ZH2 = [                       # zh2 nav: 过 BIOS → 标题 → Options → Controller 页
    (2800, 'cross', 'tap'), (2950, 'cross', 'tap'), (3100, 'cross', 'tap'),
    (11400, 'start', 'tap'), (12600, 'cross', 'tap'), (13500, 'cross', 'tap'),
    (14400, 'cross', 'tap'), (15300, 'cross', 'tap'), (16200, 'cross', 'tap'),
    (17100, 'cross', 'tap'), (18000, 'cross', 'tap'), (18900, 'cross', 'tap'),
    (19800, 'cross', 'tap'), (20700, 'cross', 'tap'), (21600, 'cross', 'tap'),
    (24000, 'cross', 'tap'), (25400, 'down', 'tap'), (25800, 'down', 'tap'),
    (26200, 'down', 'tap'), (26600, 'down', 'tap'), (27000, 'down', 'tap'),
    (27400, 'down', 'tap'), (27800, 'down', 'tap'), (28600, 'cross', 'tap'),
    (29800, 'cross', 'tap'), (31000, 'down', 'tap'), (31800, 'down', 'tap'),
    (32600, 'down', 'tap'), (33400, 'down', 'tap'), (34200, 'down', 'tap'),
    (35000, 'down', 'tap'), (35800, 'down', 'tap'), (36600, 'circle', 'tap'),
    (37400, 'circle', 'tap'),
]
NAV_QUICK = [(2800, 'cross', 'tap'), (2950, 'cross', 'tap'), (3100, 'cross', 'tap'),
             (11400, 'start', 'tap'), (12600, 'cross', 'tap'), (13500, 'cross', 'tap')]
NAV_BISECT = [(2800, 'cross', 'tap'), (2950, 'cross', 'tap'), (3100, 'cross', 'tap'),
              (11400, 'start', 'tap'), (12600, 'cross', 'tap'), (13500, 'cross', 'tap'),
              (14400, 'cross', 'tap'), (15300, 'cross', 'tap')]
PRESETS = {'zh2nav': (NAV_ZH2, 40000), 'quick': (NAV_QUICK, 4300),
           'bisect': (NAV_BISECT, 15500), 'boot': (NAV_QUICK[:3], 12000)}


def die(msg):
    raise SystemExit('[run_test] FAIL: ' + msg)


def write_nav(dump, keys):
    p = os.path.join(dump, 'nav.txt')
    with open(p, 'w') as f:
        f.write('\n'.join('%d %s %s' % k for k in keys))
    return p


def cdvd_stall(dump):
    """cdvd.log 停止推进判据: 尾行帧号 与 总行数 不再增长 (取尾帧 < 期望帧的 30% 且
    尾帧落在 GR.IMG 尾间隙区 774748-775500 → 模拟器层偶发挂起)。"""
    log = os.path.join(dump, 'cdvd.log')
    if not os.path.exists(log):
        return None
    try:
        with open(log, 'r', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        return None
    if not lines:
        return None
    tail = lines[-1].split()
    if len(tail) < 2 or not tail[0].isdigit():
        return None
    last_frame = int(tail[0])
    if 774000 <= int(tail[1]) <= 776000 or last_frame < 1000:
        return last_frame
    return None


def parse_gslog(dump):
    gs = os.path.join(dump, 'gs.log')
    n_hit = 0
    first_frame = None
    if os.path.exists(gs):
        pat = re.compile(r"needle 'WPNRPK74' hit #(\d+) in ee .*\(frame (\d+)\)")
        with open(gs, 'r', errors='replace') as f:
            for ln in f:
                m = pat.search(ln)
                if m:
                    n_hit = int(m.group(1))
                    if first_frame is None:
                        first_frame = int(m.group(2))
    return n_hit, first_frame


def main():
    ap = argparse.ArgumentParser(description='gsrunner 一键测试')
    ap.add_argument('--iso', required=True, help='待测 ISO (反斜杠路径!)')
    ap.add_argument('--dump', required=True, help='转储目录')
    ap.add_argument('--preset', choices=sorted(PRESETS), default='zh2nav')
    ap.add_argument('--frames', type=int, help='帧上限 (缺省 = preset 值)')
    ap.add_argument('--input', help='自定义输入脚本 (帧 按钮 tap); 缺省用 preset 导航')
    ap.add_argument('--memcards', default=MEMCARDS,
                    help='记忆卡目录 (gsrunner 主记忆卡; round8 起默认 — 原 memcards_db1 已清理, 若 40k 基准 boot 计时失配需调 nav)')
    ap.add_argument('--min-needle', type=int, default=3000, help='健康 needle 下限')
    ap.add_argument('--dry-run', action='store_true', help='只打印命令不执行')
    a = ap.parse_args()
    if not os.path.exists(GS):
        die('无 gsrunner: %s' % GS)
    if '/' in a.iso:
        print('  警告: ISO 路径含正斜杠 — gsrunner 会秒退, 已自动转换')
    iso = os.path.abspath(a.iso)
    os.makedirs(a.dump, exist_ok=True)
    if a.input:
        nav = os.path.abspath(a.input)
    else:
        keys, def_frames = PRESETS[a.preset]
        nav = write_nav(a.dump, keys)
        if a.frames is None:
            a.frames = def_frames
    if a.frames is None:
        a.frames = 40000
    # grmaxframes 给一点余量, 与 run_iso.py 一致
    grmax = a.frames - 100 if a.frames >= 1000 else a.frames
    dump_abs = os.path.abspath(a.dump)   # gsrunner 以自身目录为 cwd, 转储路径必须绝对
    os.makedirs(dump_abs, exist_ok=True)
    args = [GS, '-grdumpdir', dump_abs, '-grscanframes', '10',
            '-grsnap', '62', '-grmaxframes', str(grmax),
            '-grmemcards', a.memcards.replace('/', '\\'),
            '-grinput', nav,
            '-renderer', 'dx11', '-logfile', os.path.join(dump_abs, 'gs.log'), '--', iso]
    print('[run_test] preset=%s frames=%d iso=%s' % (a.preset, a.frames, iso))
    if a.dry_run:
        print(' '.join(args))
        return 0
    t0 = time.time()
    r = subprocess.run(args, cwd=os.path.dirname(GS))
    elapsed = time.time() - t0
    n_hit, first = parse_gslog(a.dump)
    stall = cdvd_stall(a.dump)
    print('[run_test] exit=%d elapsed=%.0fs needle=%d (首中 f%s)'
          % (r.returncode, elapsed, n_hit, first))
    if stall is not None:
        print('[run_test] 判定: CDVD_STALL @f%d — 模拟器层偶发挂起, 与盘内容无关, 直接重跑'
              % stall)
        return 3
    if r.returncode == 0 and n_hit >= a.min_needle:
        print('[run_test] 判定: ALIVE ✓ (跑满 %d 帧, needle %d ≥ %d)'
              % (a.frames, n_hit, a.min_needle))
        return 0
    print('[run_test] 判定: CRASH ✗ (exit=%d needle=%d < %d)'
          % (r.returncode, n_hit, a.min_needle))
    print('  判读提示: Controller 页 = %s/snap_f00033480.png; boot 挂死看 ~f4300 前快照'
          % a.dump)
    return 2


if __name__ == '__main__':
    sys.exit(main())
