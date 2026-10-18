# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/run_bisect.py (逐字复制 (15500 帧字形二分))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""run_bisect.py — 二分探针: 跑到 f15500 (Name Entry 判字形)
用法: python run_bisect.py <ISO> <DUMP>
判读: snap_f00015066.png 键盘格内有无字母
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, subprocess, sys, time

GS   = os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
iso, dump = sys.argv[1], sys.argv[2]
os.makedirs(dump, exist_ok=True)
script = os.path.join(dump, 'nav.txt')
keys = [
    (2800,'cross','tap'),(2950,'cross','tap'),(3100,'cross','tap'),
    (11400,'start','tap'),(12600,'cross','tap'),(13500,'cross','tap'),
    (14400,'cross','tap'),(15300,'cross','tap'),
]
open(script, 'w').write('\n'.join(f"{a} {b} {c}" for a, b, c in keys))

args = [GS, "-grdumpdir", dump, "-grscanframes", "10",
        "-grsnap", "62", "-grmaxframes", "15500",
        "-grmemcards", os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'memcards_db1'),
        "-grinput", script,
        "-renderer", "dx11", "-logfile", os.path.join(dump, "gs.log"), "--", iso]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print('exit=%d elapsed=%.0fs' % (r.returncode, time.time() - t0))
