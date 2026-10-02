# -*- coding: utf-8 -*-
"""run_brief2.py <dumpname> <iso> <navfile> [maxframes] [snapstep] [dwstart dwend]
Fast-nav briefing runner. Memcards copied fresh from third_party/emu/run/memcards each run.
产出按版本归档: 转储/记忆卡 → work/builds/<被测版本>/temp/。"""
import os, subprocess, sys, time, shutil

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
GS   = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC   = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')

name = sys.argv[1]
iso  = sys.argv[2]
nav  = sys.argv[3]
maxf = sys.argv[4] if len(sys.argv) > 4 else '20000'
snap = sys.argv[5] if len(sys.argv) > 5 else '100'

VER = os.path.splitext(os.path.basename(iso))[0]      # GR_ZH62.iso → GR_ZH62
TEMP = os.path.join(BUILDS, VER, 'temp')

MCD = os.path.join(TEMP, 'mc_' + name)
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
        "-renderer", "dx11", "--", iso]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print(f"exit={r.returncode} elapsed={time.time()-t0:.0f}s dump={DUMP}")
