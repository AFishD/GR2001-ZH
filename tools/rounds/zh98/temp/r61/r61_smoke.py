# -*- coding: utf-8 -*-
r"""r61_smoke.py — 冒烟测试新开关 (-grmemwatch / -grinputlive), 60 秒内出结论。

判据:
  ① memwatch.bin 有记录, 且帧号单调递增  → 内存钩子在跑
  ② 运行中往命令文件追加 "cross tap", grlog.txt 里出现 "live: cross tap at frame N"
     且 memwatch 记录的帧号在命令之后继续增长 → 运行时按键生效 (不重启)
  ③ live dump/snap/drawwin 命令都被接受 (日志有回执, 文件真的出现)
"""
import os
import shutil
import subprocess
import sys
import time

def _find_repo(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, 'tools', 'capture')) and os.path.isdir(os.path.join(d, 'work')):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    raise RuntimeError('repo root not found from %s' % start)


REPO = _find_repo(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
WORK = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r61')
DUMP = os.path.join(WORK, 'dump_smoke')
CMDF = os.path.join(WORK, 'live_smoke.txt')
ISO = os.path.abspath(sys.argv[1])
SIZE = 4
RECLEN = 12 + SIZE          # 记录 = [u32 frame][u32 addr][u32 size] + size 字节数据


def recs():
    try:
        sz = os.path.getsize(os.path.join(DUMP, 'memwatch.bin'))
    except OSError:
        return []
    n = sz // RECLEN
    out = []
    with open(os.path.join(DUMP, 'memwatch.bin'), 'rb') as f:
        for i in range(n):
            f.seek(i * RECLEN)
            b = f.read(RECLEN)
            out.append((int.from_bytes(b[0:4], 'little'), b[8:8 + SIZE].hex()))
    return out


def main():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | Stop-Process -Force'],
                   capture_output=True)
    time.sleep(0.5)
    if os.path.isdir(DUMP):
        shutil.rmtree(DUMP)
    os.makedirs(DUMP)
    mcd = os.path.join(DUMP, 'mc')
    os.makedirs(mcd)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(mcd, f))
    open(CMDF, 'w').close()

    args = [GS, '-grdumpdir', DUMP, '-grinputlive', CMDF,
            '-grmemwatch', '0x100000', str(SIZE), '1',
            '-grdrawwin', '1', '1', '-grscanframes', '1000000',
            '-grsnap', '400',
            '-grmaxframes', '4000', '-grmemcards', mcd,
            '-renderer', 'dx11', '--', ISO]
    log = open(os.path.join(WORK, 'smoke.log'), 'w', encoding='utf-8')
    p = subprocess.Popen(args, cwd=os.path.dirname(GS), stdout=log, stderr=subprocess.STDOUT)
    print('pid=%d' % p.pid, flush=True)

    def send(line):
        with open(CMDF, 'a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
        print('  >> %s  (frames so far=%d)' % (line, len(recs())), flush=True)

    # 等 GS 渲染器就绪 (太早 QueueSnapshot 会被丢弃) —— 等到 F2000
    t0 = time.time()
    while True:
        r = recs()
        if r and r[-1][0] >= 2000:
            break
        if time.time() - t0 > 180:
            print('!! 等到 %s 帧仍未到 2000' % (r[-1][0] if r else None), flush=True)
            break
        time.sleep(0.3)
    r1 = recs()
    print('① memwatch: %d 记录, 首帧=%s 末帧=%s 单调=%s'
          % (len(r1), r1[0][0] if r1 else None, r1[-1][0] if r1 else None,
             all(r1[i][0] <= r1[i + 1][0] for i in range(len(r1) - 1))), flush=True)
    f_before = r1[-1][0] if r1 else -1

    # ② 运行时按键
    send('cross tap')
    send('drawwin 200 260')
    send('snap smoke_snap')
    send('dump smoke_dump')
    time.sleep(6)
    r2 = recs()
    f_after = r2[-1][0] if r2 else -1
    print('② 按键前后: 帧 %d -> %d (增长了 %d 帧, 未重启)' % (f_before, f_after, f_after - f_before), flush=True)
    gl = os.path.join(DUMP, 'grlog.txt')
    txt = open(gl, encoding='utf-8', errors='replace').read() if os.path.isfile(gl) else ''
    for key in ('live: Cross tap', 'live: drawlog window', 'live: snap', 'live: dump',
                'memwatch active', 'live input active'):
        hit = [l for l in txt.splitlines() if key in l]
        print('   grlog "%s": %s' % (key, hit[-1] if hit else '**缺**'), flush=True)
    # ③ 产物
    for name in ('smoke_snap.png', 'smoke_dump_f%08d_eeram.bin' % 0):
        pass
    pngs = [f for f in os.listdir(DUMP) if f.startswith('smoke_snap')]
    bins = [f for f in os.listdir(DUMP) if f.startswith('smoke_dump') and f.endswith('_eeram.bin')]
    print('③ 产物: snap=%s dump=%s' % (pngs, [(b, os.path.getsize(os.path.join(DUMP, b))) for b in bins]), flush=True)
    p.wait(timeout=300)
    print('exit=%s' % p.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
