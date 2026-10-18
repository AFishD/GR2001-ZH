# -*- coding: utf-8 -*-
r"""run_ab2.py — round47 实机 A/B 驱动 v2 (自管 dump/mc 目录, 绝不与别人共目录)。

与 run_opt.py 逐项等价的关键点都照搬:
  · 每轮**从 third_party/emu/run/memcards 模板复位记忆卡** ⇒ 引导时间线可比;
  · -grscanframes 2000 -grsnap 100 -grmaxframes 32000 -renderer dx11;
  · nav = tools/capture/nav_r47.txt;
但把 -grdumpdir / -grmemcards 放在**我自己控制的目录**, 避免别的任务清理/复用。

流程:
  1. 等到"无任何 pcsx2-gsrunner 进程"且 30s 后复查仍无 (绝不并发);
  2. 修前 GR_ZH94 → cap_before/;
  3. 再等空场 → 修后 GR_ZH96_fix → cap_after/;
  4. 每轮结束后统计帧数; 若明显早死 (帧数 < 300) 则判定失败并重试 (最多 3 次/轮),
     每次重试前都重新等空场。
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
AB = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r47', 'ab')
LOG = os.path.join(AB, 'run_ab2.log')
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC_TPL = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
NAV = os.path.join(REPO, 'tools', 'capture', 'nav_menu_only.txt')
MAXF, SNAP = os.environ.get('AB_MAXF', '12000'), '100'
EXPECT_MIN = int(os.environ.get('AB_EXPECT_MIN', '100'))   # 12000/100 - 2 ≈ 118


def log(msg):
    line = '%s  %s' % (time.strftime('%H:%M:%S'), msg)
    print(line, flush=True)
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write(line + '\n')


def emu_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2-gsrunner.exe', '/NH'],
                         capture_output=True, text=True, errors='replace').stdout
    return [ln.split()[1] for ln in out.splitlines() if 'pcsx2-gsrunner' in ln]


def wait_free(tag, poll=5, need=2):
    """等到连续 need 次 (间隔 30s) 都没有仿真器进程。"""
    ok = 0
    t0 = time.time()
    while ok < need:
        p = emu_pids()
        if p:
            ok = 0
            log('%s: 等待中, pcsx2 pids=%s' % (tag, p))
            time.sleep(poll)
            continue
        ok += 1
        log('%s: 空场确认 %d/%d (pcsx2 无进程)' % (tag, ok, need))
        if ok < need:
            time.sleep(30)
    log('%s: 空场确认完毕, 等待 %.0fs' % (tag, time.time() - t0))


def reset_mc(mc):
    os.makedirs(mc, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))


def count_snaps(d):
    return len([f for f in os.listdir(d) if f.startswith('snap_')]) if os.path.isdir(d) else -1


def run_round(tag, iso, dump, mc):
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    reset_mc(mc)
    args = [GS, '-grdumpdir', dump, '-grscanframes', '2000', '-grsnap', SNAP,
            '-grmaxframes', MAXF, '-grmemcards', mc, '-grinput', NAV,
            '-renderer', 'dx11', '--', iso]
    log('%s: 启动 %s' % (tag, ' '.join(args)))
    t0 = time.time()
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write('--- %s gsrunner 输出开始 ---\n' % tag)
        f.flush()
        r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=f,
                           stderr=subprocess.STDOUT)
        f.write('--- %s gsrunner 输出结束 rc=%s ---\n' % (tag, r.returncode))
    n = count_snaps(dump)
    log('%s: 结束 rc=%s 用时 %.0fs 帧数=%d (期望>=%d)' % (tag, r.returncode, time.time() - t0,
                                                        n, EXPECT_MIN))
    return n


def round_with_retry(tag, iso, dump, mc, tries=3):
    for k in range(1, tries + 1):
        wait_free('%s 第%d次' % (tag, k))
        n = run_round('%s 第%d次' % (tag, k), iso, dump, mc)
        if n >= EXPECT_MIN:
            return n
        log('%s: 帧数不足 (%d < %d) ⇒ 判定早死, 准备重试' % (tag, n, EXPECT_MIN))
    return -1


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else 'both'      # both | before | after
    nv = hashlib.sha256(open(NAV, 'rb').read()).hexdigest()
    log('=== AB v2 start (want=%s) ===  现有 pcsx2 pids=%s' % (want, emu_pids()))
    log('nav = %s  sha256=%s' % (NAV, nv))
    nb = na = -2
    if want in ('both', 'before'):
        nb = round_with_retry('修前 GR_ZH94', os.path.join(REPO, 'work', 'builds', 'GR_ZH94',
                                                           'GR_ZH94.iso'),
                              os.path.join(AB, 'cap_before'), os.path.join(AB, 'mc_before'))
    if want in ('both', 'after'):
        na = round_with_retry('修后 GR_ZH96_fix', os.path.join(REPO, 'work', 'builds',
                                                               'GR_ZH96_fix',
                                                               'GR_ZH96_fix.iso'),
                              os.path.join(AB, 'cap_after'), os.path.join(AB, 'mc_after'))
    log('=== AB v2 done: before=%d 帧 after=%d 帧 ===' % (nb, na))
    log('   before=%s' % os.path.join(AB, 'cap_before'))
    log('   after =%s' % os.path.join(AB, 'cap_after'))


if __name__ == '__main__':
    main()
