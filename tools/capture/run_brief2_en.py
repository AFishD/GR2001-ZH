# -*- coding: utf-8 -*-
"""run_brief2_en.py <dumpname> <navfile> [maxframes] [snapstep] — EN 原盘 run。

EN 原盘 = third_party/orig/ps2/Tom Clancy's Ghost Recon (USA).iso。
记忆卡: 原用会话副本 work/zh16b/subagent_l1panel3/mcb_en (已随会话清理),
现缺省用仓库标准记忆卡 third_party/emu/run/memcards (boot→简报导航无需存档)。
产出按版本归档: 转储/记忆卡 → work/builds/GR_EN_ORIG/temp/ (EN 基线夹)。"""
import os, subprocess, sys, time, shutil
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
GS   = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC   = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
ISO  = os.path.join(REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso")
name = sys.argv[1]
nav  = sys.argv[2]
maxf = sys.argv[3] if len(sys.argv) > 3 else '11000'
snap = sys.argv[4] if len(sys.argv) > 4 else '50'
TEMP = os.path.join(BUILDS, 'GR_EN_ORIG', 'temp')
MCD = os.path.join(TEMP, 'mce_' + name)
if os.path.isdir(MCD): shutil.rmtree(MCD)
os.makedirs(MCD)
for f in ('Mcd001.ps2', 'Mcd002.ps2'):
    shutil.copy2(os.path.join(MC, f), os.path.join(MCD, f))
DUMP = os.path.join(TEMP, 'dump_' + name)
if os.path.isdir(DUMP): shutil.rmtree(DUMP)
os.makedirs(DUMP)
navp = os.path.join(TEMP, nav)
if not os.path.isfile(navp):                     # nav 随库分发在 tools/capture/ 下
    alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), nav)
    if os.path.isfile(alt):
        navp = alt
args = [GS, "-grdumpdir", DUMP, "-grdrawwin", "3300", maxf,
        "-grscanframes", "2000", "-grsnap", snap, "-grmaxframes", maxf,
        "-grmemcards", MCD, "-grinput", navp,
        "-renderer", "dx11", "--", ISO]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print(f"exit={r.returncode} elapsed={time.time()-t0:.0f}s")
