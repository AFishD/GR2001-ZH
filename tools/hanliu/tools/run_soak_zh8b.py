# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/run_soak_zh8b.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""run_soak_zh8b.py — GR_ZH8b 150000 帧浸泡 (nav_soak: Controller 页驻留 + 每 2400 帧 down)
用法: python run_soak_zh8b.py
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, subprocess, sys, time
GS = os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
ISO = os.path.join(REPO_ROOT, 'build', 'iso', 'GR_ZH8b.iso')
DUMP = os.path.join(REPO_ROOT, 'test_results', 'zh8b_soak')
os.makedirs(DUMP, exist_ok=True)
nav = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh7q', 'nav_soak.txt')
args = [GS, "-grdumpdir", DUMP, "-grscanframes", "10",
        "-grsnap", "310", "-grmaxframes", "150000",
        "-grmemcards", os.path.join(REPO_ROOT, 'tools', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'memcards_db1'),
        "-grinput", nav,
        "-renderer", "dx11", "-logfile", os.path.join(DUMP, "gs.log"), "--", ISO]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print('soak exit=%d elapsed=%.0fs' % (r.returncode, time.time() - t0))
