# -*- coding: utf-8 -*-
r"""r61_recon.py — 只读侦察 (round61 第 1 步的"读哪里")

目的: 用新开关 `-grinputlive` (运行时按键) + `-grmemwatch` (心跳/帧号) 驱动游戏
走到「特别收录」列表, 在**每一个选中行**上各做一次全 EE RAM dump + 截图, 供
Python 端差分出"随选中行变化"的变量候选。

为什么需要它: 闭环导航要求一个确定性的"当前选中行"观测值; drawlog 只告诉我们
"画了什么文本"(10 行标签每帧都画), 不告诉我们"哪一行被选中"。内存里一定有这个
状态, 差分是找到它最直接的办法。

判据 (运行后由 r61_diff_rows.py 出): 找到地址 A, 其值在 9 个采样点上依次等于
列表序号 [0,1,2,3,4,5,7,8,9] (第 7 行「专家」是灰色空条, 光标自动跳过)。

时序: 抄 tools/capture/nav_sf_interview.txt 的前半段 (round60 实机验证过能进
「特别收录」列表), 后半段改成"每行停 500 帧 → dump + snap"。

用法: python work/builds/GR_ZH98/temp/r61/r61_recon.py <iso> <tag> [maxframes]
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

# 心跳区间: 只是为了让 Python 随时知道"当前帧号"; 读 4 字节, 无副作用
HB_ADDR = 0x00100000
HB_SIZE = 4
RECLEN = 12 + HB_SIZE   # 记录 = [u32 frame][u32 addr][u32 size] + size 字节数据


def kill_stale():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        'Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | '
                        'Stop-Process -Force; Start-Sleep -Milliseconds 400'],
                       capture_output=True, text=True)
    return r.returncode


class Runner:
    def __init__(self, iso, tag, maxframes):
        self.tag = tag
        self.dump = os.path.join(WORK, 'dump_' + tag)
        self.cmd = os.path.join(WORK, 'live_%s.txt' % tag)
        self.log = os.path.join(WORK, 'recon_%s.log' % tag)
        self.mc = os.path.join(self.dump, 'mc')
        if os.path.isdir(self.dump):
            shutil.rmtree(self.dump)
        os.makedirs(self.dump)
        os.makedirs(self.mc, exist_ok=True)
        for f in ('Mcd001.ps2', 'Mcd002.ps2'):
            shutil.copy2(os.path.join(MC, f), os.path.join(self.mc, f))
        open(self.cmd, 'w', encoding='utf-8').close()
        self.mw = os.path.join(self.dump, 'memwatch.bin')
        self.maxframes = maxframes
        self.iso = iso
        self.proc = None

    def start(self):
        args = [GS,
                '-grdumpdir', self.dump,
                '-grinputlive', self.cmd,
                '-grmemwatch', str(HB_ADDR), str(HB_SIZE), '1',
                '-grdrawwin', '1', '1',          # 先开文件, 窗口只覆盖 F1; 之后用 live drawwin 改
                '-grscanframes', '1000000',      # 关掉 needle 扫描 (省时间)
                '-grsnap', '200',
                '-grmaxframes', str(self.maxframes),
                '-grmemcards', self.mc,
                '-renderer', 'dx11',
                '--', self.iso]
        self.logf = open(self.log, 'w', encoding='utf-8')
        self.logf.write(' '.join(args) + '\n')
        self.logf.flush()
        self.proc = subprocess.Popen(args, cwd=os.path.dirname(GS),
                                     stdout=self.logf, stderr=subprocess.STDOUT)
        return self.proc

    # ---- 帧号 (心跳) ----
    def frame_now(self):
        try:
            sz = os.path.getsize(self.mw)
        except OSError:
            return -1
        n = sz // RECLEN
        if n == 0:
            return -1
        with open(self.mw, 'rb') as f:
            f.seek((n - 1) * RECLEN)
            b = f.read(RECLEN)
        if len(b) < RECLEN:
            return -1
        return int.from_bytes(b[0:4], 'little')

    def wait_frame(self, t, timeout=180.0):
        t0 = time.time()
        while True:
            f = self.frame_now()
            if f >= t:
                return f
            if self.proc.poll() is not None:
                raise RuntimeError('emulator exited early (rc=%s) at frame %s' % (self.proc.returncode, f))
            if time.time() - t0 > timeout:
                raise TimeoutError('wait_frame(%d) timeout, now=%s' % (t, f))
            time.sleep(0.05)

    def send(self, line):
        with open(self.cmd, 'a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
        print('  [%7s] >> %s' % (self.frame_now(), line), flush=True)

    def tap(self, btn):
        self.send('%s tap' % btn)


def main():
    iso = os.path.abspath(sys.argv[1])
    tag = sys.argv[2]
    maxframes = int(sys.argv[3]) if len(sys.argv) > 3 else 40000
    kill_stale()
    r = Runner(iso, tag, maxframes)
    print('ISO  = %s' % iso)
    print('dump = %s' % r.dump)
    print('cmd  = %s' % r.cmd)
    r.start()
    print('pid  = %d' % r.proc.pid)

    # ---------- 前半段: 跳过片头 → 选择文件 → 主菜单 (抄 nav_sf_interview.txt) ----------
    for f in range(800, 2700, 200):
        r.wait_frame(f)
        r.tap('start')
    for f in (2850, 2950, 3050):
        r.wait_frame(f)
        r.tap('up')
    r.wait_frame(3250)
    r.tap('cross')
    print('  ... 等待开场动画 / 主菜单 (到 F10600)', flush=True)

    # ---------- 主菜单: up×9 钉顶 ----------
    for i, f in enumerate(range(10600, 15100, 500)):
        r.wait_frame(f)
        r.tap('up')
    print('  主菜单 up×9 完成, 等待进入特别收录列表', flush=True)

    # ---------- 特别收录列表: 逐行采样 ----------
    t = 15200
    r.wait_frame(t)
    print('=== 列表采样开始 (每行 dump + snap) ===', flush=True)
    for k in range(9):                      # 1-based 行号 = [1,2,3,4,5,6,8,9,10]
        if k > 0:
            t += 500
            r.wait_frame(t)
            r.tap('down')
        t += 500
        r.wait_frame(t)
        r.send('dump row%02d' % k)
        r.send('snap row%02d' % k)
        r.wait_frame(t + 300)               # 让 32MB 落盘
    # ---------- 回到「访谈」(1-based 第 9 行 = 采样点 k=7) ----------
    t += 500
    r.wait_frame(t)
    r.tap('up')                             # 预告片(第10行) → 访谈(第9行)
    t += 500
    r.wait_frame(t)
    r.send('dump row_interview')
    r.send('snap row_interview')
    r.wait_frame(t + 300)
    # ---------- cross 打开「开发访谈 1」 ----------
    t += 500
    r.wait_frame(t)
    r.tap('cross')
    t += 1400
    r.wait_frame(t)
    r.send('snap page_interview')
    r.send('dump page_interview')
    r.send('drawwin %d %d' % (t - 900, t + 900))
    r.wait_frame(t + 400)
    r.send('snap page_interview_settled')
    # ---------- 页内: 试各种"翻页"键, 各拍一张 ----------
    for i, btn in enumerate(('down', 'down', 'right', 'l1', 'r1', 'left')):
        t += 500
        r.wait_frame(t)
        r.tap(btn)
        t += 500
        r.wait_frame(t)
        r.send('snap page_try%d_%s' % (i, btn))
    r.send('drawwin %d %d' % (t - 2500, t + 200))
    print('=== 采样结束, 等模拟器到 maxframes=%d ===' % maxframes, flush=True)
    rc = r.proc.wait()
    print('exit=%s' % rc)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
