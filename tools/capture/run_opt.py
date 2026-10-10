# -*- coding: utf-8 -*-
"""run_opt.py <dumpname> <navfile> [maxframes] [snapstep] [drawwin_start drawwin_end]
Boot-to-main-menu nav runner. ISO 缺省 = work/builds/ 下版本号最大构筑 (GR_ISO 环境变量可覆盖)。
产出按版本归档: 转储 → work/builds/<版本>/temp/dump_<name>/;
记忆卡 = work/builds/<版本>/temp/mc/ 常驻副本 (首跑自动从 third_party/emu/run/memcards 补齐, 保留已有存档)。"""
import os, subprocess, sys, time, shutil, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
GS   = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC   = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')


def latest_iso():
    best = (-1, None)
    for d in os.listdir(BUILDS):
        m = re.fullmatch(r'GR_ZH(\d+)', d)
        if m and os.path.isfile(os.path.join(BUILDS, d, d + '.iso')):
            best = max(best, (int(m.group(1)), os.path.join(BUILDS, d, d + '.iso')))
    return best[1]


ISO = os.environ.get('GR_ISO') or latest_iso()
assert ISO, 'work/builds 下无构筑 ISO (用 make_build.py 先构筑, 或设 GR_ISO 环境变量)'
_d = os.path.dirname(os.path.abspath(ISO))
VER = os.path.basename(_d) if os.path.basename(os.path.dirname(_d)) == 'builds' \
    else os.path.splitext(os.path.basename(ISO))[0]
TEMP = os.path.join(BUILDS, VER, 'temp')

name = sys.argv[1] if len(sys.argv) > 1 else 'run1'
nav  = sys.argv[2] if len(sys.argv) > 2 else 'nav_probeA.txt'
maxf = sys.argv[3] if len(sys.argv) > 3 else '31000'
snap = sys.argv[4] if len(sys.argv) > 4 else '100'

MCD = os.path.join(TEMP, 'mc')
os.makedirs(MCD, exist_ok=True)
# ★ 每轮从模板重建干净记忆卡 (关键):
#   游戏在 temp/mc 里写存档后, 卡片剩余空间变化 → 开机 BIOS 的记忆卡空间检查耗时变化
#   → 引导阶段出现"请插入至少有500KB空闲空间的记忆卡/按×继续"阻塞, 实测 F400~F3450 逐帧相同,
#   主菜单从 F3304 漂到 ~F6000 → **绝对帧号全部失效**(同一导航在不同盘/不同批次结果不同)。
#   故每轮强制复位为模板副本, 保证引导时间线稳定可比。
#   环境变量 GR_KEEP_MC=1 保留卡片(调试存档相关问题时用)。
if os.environ.get('GR_KEEP_MC') != '1':
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(MCD, f))
else:
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        dst = os.path.join(MCD, f)
        if not os.path.isfile(dst):
            shutil.copy2(os.path.join(MC, f), dst)

DUMP = os.path.join(TEMP, 'dump_' + name)
if os.path.isdir(DUMP): shutil.rmtree(DUMP)
os.makedirs(DUMP)
navp = os.path.join(TEMP, nav)
if not os.path.isfile(navp):                     # nav 随库分发在 tools/capture/ 下
    alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), nav)
    if os.path.isfile(alt):
        navp = alt

args = [GS, "-grdumpdir", DUMP, "-grscanframes", "2000",
        "-grsnap", snap, "-grmaxframes", maxf,
        "-grmemcards", MCD,
        "-grinput", navp,
        "-renderer", "dx11", "--", ISO]
extra = sys.argv[5:]
if extra:
    args = [GS, "-grdumpdir", DUMP, "-grdrawwin", extra[0], extra[1],
            "-grscanframes", "2000", "-grsnap", snap, "-grmaxframes", maxf,
            "-grmemcards", MCD, "-grinput", navp,
            "-renderer", "dx11", "--", ISO]
t0 = time.time()
r = subprocess.run(args, cwd=os.path.dirname(GS))
print(f"exit={r.returncode} elapsed={time.time()-t0:.0f}s dump={DUMP}")
