# -*- coding: utf-8 -*-
r"""fix_zh118_run.py - round72: run gsrunner on a .p2s state, scripted pad input,
wall-clock timeout, capture of the emulator's own stdout/stderr (so a
"Jump to unmapped recLUT page" ReportErrorAsync is visible).

Adds over fix_zh116_run.py:
  --outroot <dir>   artifact root (default work/builds/GR_ZH118/temp)
  --timeout <s>     kill the process after N seconds (paused VM never exits)
  --grswitch        extra raw switches appended verbatim (repeatable)

Usage:
  python tools/iso_build/fix_zh118_run.py --iso work/builds/GR_ZH111/GR_ZH111.iso \
      --tag fire111 --state "work/temp/NEW_Mem/SLUS-20613 (7A361FB5).01.p2s" \
      --snap 15 --pcsample --input work/builds/GR_ZH118/temp/nav_fire.txt \
      --memcards work/builds/GR_ZH118/temp/mc --timeout 240
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
DEFAULT_OUTROOT = os.path.join(REPO, 'work', 'builds', 'GR_ZH118', 'temp')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--state', default=None)
    ap.add_argument('--maxframes', type=int, default=3000)
    ap.add_argument('--snap', type=int, default=60)
    ap.add_argument('--live', default=None)
    ap.add_argument('--input', default=None, help='frame-indexed -grinput file')
    ap.add_argument('--memwatch', action='append', default=[])
    ap.add_argument('--drawlog', default=None, help='<start> <end>')
    ap.add_argument('--pcsample', action='store_true')
    ap.add_argument('--pcring', default=None,
                    help='N: executed-block PC ring (implies trace-all-blocks); '
                         'writes reclut_crash.txt on a recLUT trap')
    ap.add_argument('--grswitch', action='append', default=[],
                    help='raw extra switch group, e.g. --grswitch "-grpcling 256"')
    ap.add_argument('--memcards', default=None)
    ap.add_argument('--renderer', default='dx11')
    ap.add_argument('--outroot', default=DEFAULT_OUTROOT)
    ap.add_argument('--timeout', type=int, default=0, help='0 = no timeout')
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()

    dump = os.path.join(a.outroot, 'dump_' + a.tag)
    if os.path.isdir(dump) and not a.keep:
        shutil.rmtree(dump)
    os.makedirs(dump, exist_ok=True)

    mc = a.memcards
    if mc and not os.path.isdir(mc):
        os.makedirs(mc, exist_ok=True)

    args = [GS, '-grdumpdir', dump, '-grsnap', str(a.snap),
            '-grmaxframes', str(a.maxframes), '-grscanframes', '1000000',
            '-logfile', os.path.join(dump, 'emulog.txt'),
            '-renderer', a.renderer]
    if mc:
        args += ['-grmemcards', mc]
    if a.state:
        args += ['-grstate', os.path.abspath(a.state)]
    if a.live:
        args += ['-grinputlive', os.path.abspath(a.live)]
    if a.input:
        args += ['-grinput', os.path.abspath(a.input)]
    if a.pcsample:
        args += ['-grpcsample', '1']
    if a.pcring:
        args += ['-grpcring', str(a.pcring)]
    for m in a.memwatch:
        args += ['-grmemwatch'] + m.split()
    if a.drawlog:
        args += ['-grdrawwin'] + a.drawlog.split()
    for s in a.grswitch:
        args += s.split()
    args += ['--', os.path.abspath(a.iso)]

    conlog = os.path.join(dump, 'console.txt')
    print('RUN: ' + ' '.join('"%s"' % x if ' ' in x else x for x in args))
    print('CONSOLE -> ' + conlog)
    t0 = time.time()
    rc = None
    timed_out = False
    with open(conlog, 'wb') as fo:
        p = subprocess.Popen(args, cwd=os.path.dirname(GS), stdout=fo, stderr=subprocess.STDOUT)
        try:
            rc = p.wait(timeout=(a.timeout or None))
        except subprocess.TimeoutExpired:
            timed_out = True
            p.kill()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                pass
            rc = p.returncode
    el = time.time() - t0
    print('exit=%s timed_out=%s elapsed=%.0fs dump=%s' % (rc, timed_out, el, dump))
    try:
        txt = open(conlog, 'rb').read().decode('utf-8', 'replace')
    except OSError:
        txt = ''
    hits = [l for l in txt.splitlines() if 'recLUT' in l or 'Exception' in l or 'GR: ' in l]
    if hits:
        print('--- console highlights (%d) ---' % len(hits))
        for l in hits[-60:]:
            print('  ' + l.strip())
    return 0 if rc == 0 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
