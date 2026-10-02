# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/run_iso.py (逐字复制 (zh2 nav 40000 帧 gsrunner))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""run_iso.py — 参数化 40000 帧 gsrunner 实测 (zh2 nav, memcards_db1)
用法: python run_iso.py <ISO 反斜杠路径> <DUMP 反斜杠路径>
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, subprocess, sys, time

GS = os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
iso, dump = sys.argv[1], sys.argv[2]
os.makedirs(dump, exist_ok=True)
script = os.path.join(dump, 'nav.txt')
keys = [
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
open(script, 'w').write('\n'.join(f"{a} {b} {c}" for a, b, c in keys))

args = [GS, "-grdumpdir", dump, "-grscanframes", "10",
        "-grsnap", "62", "-grmaxframes", "39900",
        "-grmemcards", os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'memcards_db1'),
        "-grinput", script,
        "-renderer", "dx11", "-logfile", os.path.join(dump, "gs.log"), "--", iso]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print('exit=%d elapsed=%.0fs' % (r.returncode, time.time() - t0))
