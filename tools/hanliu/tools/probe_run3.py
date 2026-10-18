# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/probe_run3.py (逐字复制 (4300 帧快判))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""probe_run3.py — boot 判定短跑 (反斜杠路径版)
用法: python probe_run3.py <ISO反斜杠路径> <DUMP反斜杠路径>
判据: cdvd.log 末帧 >= 4100 = 活; 否则 = 毒(挂死于 boot ~f2817)
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, subprocess, sys, time

GS   = os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
iso, dump = sys.argv[1], sys.argv[2]
os.makedirs(dump, exist_ok=True)
script = os.path.join(dump, 'nav.txt')
keys = [(2800, 'cross', 'tap'), (2950, 'cross', 'tap'), (3100, 'cross', 'tap')]
open(script, 'w').write('\n'.join('%d %s %s' % k for k in keys))

args = [GS, "-grdumpdir", dump, "-grscanframes", "10",
        "-grsnap", "62", "-grmaxframes", "4300",
        "-grmemcards", os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'memcards_db1'),
        "-grinput", script,
        "-renderer", "dx11", "-logfile", os.path.join(dump, "gs.log"), "--", iso]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print('exit=%d elapsed=%.0fs' % (r.returncode, time.time() - t0))

last_frame, last_lba, n = 0, 0, 0
for line in open(os.path.join(dump, 'cdvd.log'), encoding='latin-1', errors='replace'):
    p = line.split()
    if len(p) == 2:
        last_frame, last_lba = int(p[0]), int(p[1]); n += 1
alive = last_frame >= 4100
print('VERDICT:', ('ALIVE cdvd末读 f%d LBA%d (%d行)' % (last_frame, last_lba, n)) if alive
      else ('HUNG cdvd静默 f%d LBA%d (%d行)' % (last_frame, last_lba, n)))
