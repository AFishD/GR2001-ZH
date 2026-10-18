# -*- coding: utf-8 -*-
r"""nav_hook.py — 闭环状态机导航: 用**模拟器内存钩子**读实际选中项, 边按边校验 (round61)

与 nav_state.py 的根本区别
--------------------------
nav_state.py: 观测 = 跑完一轮后的 drawlog 文本 → 决策 → **重启模拟器再跑一轮** (~505 s/轮);
              按键时序在启动时固定 (`-grinput`), 运行中不可改 ⇒ 只能"事后纠偏", 不能闭环。
nav_hook.py : 观测 = 模拟器**内存钩子** `-grmemwatch` 每帧输出的 EE RAM 值 (选中项号);
              执行 = `-grinputlive` 运行时按键文件, 每帧轮询, **不重启**;
              ⇒ 真正的闭环: 读状态 → 判位置 → 按键 → 再读状态校验, 每一步都验。

为什么必须闭环 (round61 实测)
----------------------------
`tools/capture/nav_sf_interview.txt` 那种固定帧时序**很脆**: 同一份时间线, 用 `-grinput`
(12 帧长按) 能进「特别收录」, 换成 `-grinputlive` (3 帧短按) 就只走到主菜单, 9 个采样点
全部落在主菜单上。差一次按键/差一个落点, 后面全错。所以本轮把"当前选中项"变成**可读的
状态量**, 每一步都拿它校验。

两个新开关 (本轮加进 third_party/emu/pcsx2_src/pcsx2-gsrunner/GRResearch.cpp)
----------------------------------------------------------------------------
  -grmemwatch <addr> <size> <interval>   每 interval 帧往 <dumpdir>/memwatch.bin 追加定长记录
                                         [u32 frame][u32 addr][u32 size] + size 字节
                                         (共享打开 DenyNone ⇒ 外部进程可实时 tail; **可重复给**,
                                         多个区间写同一个文件, 读侧按记录里的 addr 分流)
  -grinputlive <file>                    每帧轮询该文件, 新追加的行立刻注入 (不重启):
                                           <btn> tap|release|hold   按键 (tap = 3 帧短按)
                                           dump <tag>               立刻 dump 全 EE+IOP RAM
                                           snap <tag>               立刻截图 → <tag>.png
                                           drawwin <a> <b>          运行时改 drawlog 窗口
  -grdrawwin 1 1                         启动只开文件不记内容, 之后用 live `drawwin` 开窗口

两段闭环 (round61 实测标定)
--------------------------
  主菜单 (9 项, 第 4 项「快速任务」是灰条被跳过):
      钩子 0x013379D0 = 1-based 项号, 值域 {1,2,3,5,6,7,8,9}
      「特别收录」= 7
  特别收录列表 (10 项, 第 7 项「专家」是灰条被跳过):
      SF_SEL_ADDR / SF_ROWS 见下方标定值
      「访谈」= 倒数第二项

用法:
  python tools/capture/nav_hook.py GR_TEST_FONT2 [--iso PATH] [--tag hook1]
         [--maxframes 40000] [--snap 500] [--no-page-tries]
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


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


REPO = _find_repo(HERE)
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
BUILDS = os.path.join(REPO, 'work', 'builds')

# ===================== round61 实测标定 =====================
# 主菜单: 9 项 (训练/战术演习/战役/[快速任务·灰条]/多人游戏/统计/特别收录/选项/制作组)
MENU_SEL_ADDR = 0x013379D0
MENU_ROWS = [1, 2, 3, 5, 6, 7, 8, 9]
MENU_LABELS = ['训练', '战术演习', '战役', '多人游戏', '统计', '特别收录', '选项', '制作组']
MENU_TARGET_IDX = 5                       # 「特别收录」
# 特别收录列表: 10 项 (影片/设定图/音乐/武器/奖章/背景/[专家·灰条]/屏幕截图/访谈/预告片)
#
# ★ round61 侦察结论 (重要): 特别收录列表的"当前行"**不是** EE/IOP RAM 里的标量下标。
#   已系统排除: u32 / float32 / u8 三种解释 × {1-based, 0-based, 可选行序号, 反向, 前/后一行}
#   全部假设, 在 EE 主存 (32 MB) 与 IOP RAM (2 MB) 上都是 0 命中。
#   实际表示法 = **每个列表项对象一个"选中"标志位**:
#       第1行 0x0091E7F8 / 第2行 0x0091EC88 / 第3行 0x0091F0F8 / 第4行 0x0091F508 /
#       第5行 0x0091F918 / 第6行 0x0091FD28 / (第7行「专家」灰条, 光标跳过, 无标志) /
#       第8行 0x00920588 / 第9行 0x00920988 / 第10行 0x0091CE68
#   相邻项对象相差 ~0x410 B; 跳过灰条那一步正好跨 0x860 (= 2 项) —— 与实测行序完全吻合。
#   ⇒ 因此特别收录这一段用**两种观测**互相印证:
#       (1) 内存标志位差分 (主): 每次按键后, 在被监视区间里找"0→1"和"1→0"的那一对字节,
#           要求恰好一对 ⇒ 证明"选中态真的从一项移到了另一项"(这正是上一轮丢键/重键的失效模式);
#       (2) 渲染高亮条 y (锚): 从抓到的帧上量金带中心 y, 直接给出**第几行** (与内存无关的旁证)。
#   两者都在 ⇒ 判定可信; 内存区间因堆布局变化而失效时, 退化为只用 (2), 并如实记录。
SF_SEL_ADDR = 0x0091C000                  # 监视区间起点 (覆盖上面 10 个标志位)
SF_SEL_SIZE = 0x6000                      # 24 KB
SF_ROWS = [1, 2, 3, 4, 5, 6, 8, 9, 10]    # 可选行 1-based 行号 (灰条 #7 跳过)
SF_LABELS = ['影片', '设定图', '音乐', '武器', '奖章', '背景', '屏幕截图', '访谈', '预告片']
SF_TARGET_IDX = 7                         # 「访谈」= SF_ROWS[7] = 第 9 行
# 实测金带中心 y (r61_check_rows.py 量出来的; 第 7 行灰条 y=248 光标永远不去)
SF_ROW_Y = {1: 83, 2: 111, 3: 138, 4: 165, 5: 193, 6: 220, 7: 248, 8: 275, 9: 302, 10: 329}
# ===========================================================

SETTLE_FRAMES = 14               # 按键后要求钩子值稳定的帧数
PRESS_TIMEOUT = 260              # 单次按键等待生效的帧上限
MAX_REPIN = 3                    # 漂移后重新钉顶的次数上限
# 引导时间线 (抄 nav_sf_interview.txt 前半段; 这一段落点是**主菜单**, 之后一律闭环)
BOOT_STARTS = list(range(800, 2700, 200))
BOOT_UPS = (2850, 2950, 3050)
BOOT_CROSS = 3250


def dec_bytes(b):
    """码表解码 (与 nav_state.py 同一套; 只用于把 drawlog 读成人话)"""
    ch = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                     'charset_compiled_zh16.json'), encoding='utf-8'))
    dc = {v: k for k, v in ch['codes'].items()}
    dp = {tuple(v): k for k, v in ch['pair_of'].items()}
    o, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            o.append(chr(b[i])); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in dp:
            o.append(dp[(b[i], b[i + 1])]); i += 2
        elif b[i] in dc:
            o.append(dc[b[i]]); i += 1
        else:
            i += 1
    return ''.join(o)


class Emu:
    """一次实机运行 + 内存钩子读写 + 运行时按键

    watches = [(addr, size, interval), ...]; 全部 interval 必须为 1 (每帧都采)。
    文件布局 = 逐帧拼接: [r1 记录][r2 记录]...[r1][r2]..., 每帧 stride = Σ(12+size_i)。
    读侧只取**最后一整帧**, 所以读取量 = 一帧的大小 (与运行时长无关)。
    """

    def __init__(self, iso, dump, cmd, watches, maxframes, snap):
        self.iso = iso
        self.dump = dump
        self.cmd = cmd
        self.watches = watches
        assert all(w[2] == 1 for w in watches), '所有 -grmemwatch 的 interval 必须为 1'
        self.offsets = {}
        off = 0
        for addr, size, _iv in watches:
            self.offsets[addr] = (off, size)
            off += 12 + size
        self.frame_stride = off
        self.maxframes = maxframes
        self.snap = snap
        self.proc = None
        self.events = []          # (frame, 钩子值, 说明) —— 给报告用的钩子值序列
        self.mw = os.path.join(dump, 'memwatch.bin')

    def start(self):
        args = [GS, '-grdumpdir', self.dump, '-grinputlive', self.cmd]
        for addr, size, iv in self.watches:
            args += ['-grmemwatch', '0x%08X' % addr, str(size), str(iv)]
        args += ['-grdrawwin', '1', '1',
                 '-grscanframes', '1000000',
                 '-grsnap', str(self.snap),
                 '-grmaxframes', str(self.maxframes),
                 '-grmemcards', os.path.join(self.dump, 'mc'),
                 '-renderer', 'dx11', '--', self.iso]
        self.logf = open(os.path.join(self.dump, 'emulator.log'), 'w', encoding='utf-8')
        self.logf.write(' '.join(args) + '\n')
        self.logf.flush()
        self.proc = subprocess.Popen(args, cwd=os.path.dirname(GS),
                                     stdout=self.logf, stderr=subprocess.STDOUT)

    # ---- 钩子读 (帧号与值同源, 天然一致) ----
    def frame_bytes(self):
        """返回 (frame, {addr: bytes}) —— 最后一整帧; 无数据时 (None, {})"""
        try:
            sz = os.path.getsize(self.mw)
        except OSError:
            return None, {}
        nf = sz // self.frame_stride
        if nf == 0:
            return None, {}
        try:
            with open(self.mw, 'rb') as f:
                f.seek((nf - 1) * self.frame_stride)
                buf = f.read(self.frame_stride)
        except OSError:
            return None, {}
        if len(buf) < self.frame_stride:
            return None, {}
        fr = int.from_bytes(buf[0:4], 'little')
        out = {}
        for addr, (off, size) in self.offsets.items():
            out[addr] = buf[off + 12:off + 12 + size]
        return fr, out

    def sample(self, addr=None):
        """addr=None 时返回 (frame, 第一个区间的 u32 值); 否则返回 (frame, 该区间的 u32 值)"""
        fr, fb = self.frame_bytes()
        if fr is None:
            return None, None
        if addr is None:
            addr = self.watches[0][0]
        b = fb.get(addr)
        if b is None or len(b) < 4:
            return fr, None
        return fr, int.from_bytes(b[0:4], 'little')

    def region(self, addr):
        fr, fb = self.frame_bytes()
        return fr, fb.get(addr)

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def wait_frame(self, t, timeout=300.0):
        t0 = time.time()
        while True:
            f, _ = self.sample()
            if f is not None and f >= t:
                return f
            if not self.alive():
                raise RuntimeError('模拟器提前退出 rc=%s (frame=%s)' % (self.proc.returncode, f))
            if time.time() - t0 > timeout:
                raise TimeoutError('wait_frame(%d) 超时, 当前 frame=%s' % (t, f))
            time.sleep(0.03)

    def send(self, line):
        with open(self.cmd, 'a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
        fr, v = self.sample()
        self.events.append((fr, v, '>> ' + line))
        print('   [F%-7s 钩子=%-4s] >> %s' % (fr, v, line), flush=True)

    def tap(self, btn):
        self.send('%s tap' % btn)


def press_verified(emu, addr, btn, expect, what):
    """按一次键, 等钩子值变成 expect 并稳定 SETTLE_FRAMES 帧。返回 True/False。"""
    f0, v0 = emu.sample(addr)
    emu.tap(btn)
    deadline = (f0 or 0) + PRESS_TIMEOUT
    while True:
        f, v = emu.sample(addr)
        if f is not None and f >= deadline:
            emu.events.append((f, v, '!! %s: 期望 %s 实际 %s (超时)' % (what, expect, v)))
            print('   !! %s 超时: 期望钩子=%s, 实际=%s' % (what, expect, v), flush=True)
            return False
        if v == expect:
            fstab = f + SETTLE_FRAMES
            while True:
                f2, v2 = emu.sample(addr)
                if f2 is not None and f2 >= fstab:
                    break
                if not emu.alive():
                    return False
                time.sleep(0.02)
            if v2 == expect:
                emu.events.append((f, v, 'OK %s: %s -> %s' % (what, v0, v)))
                print('   OK %s: 钩子 %s -> %s' % (what, v0, v), flush=True)
                return True
        if not emu.alive():
            return False
        time.sleep(0.02)


def pin_top(emu, addr, rows):
    """钉顶: 按 up 直到钩子值 == rows[0]; 值连续两次不变 = 已到顶/卡死。"""
    print('   -- 钉顶 (up until 钩子==%s) --' % rows[0])
    same = 0
    last = None
    for _ in range(14):
        _, v = emu.sample(addr)
        if v == rows[0]:
            print('   已在顶部 (钩子=%s)' % v, flush=True)
            return True
        if v == last:
            same += 1
            if same >= 2:
                print('   !! 连按 up 钩子值不变 (%s) —— 该列表可能还没激活' % v, flush=True)
                return False
        else:
            same = 0
        last = v
        nxt = rows[(rows.index(v) - 1) % len(rows)] if v in rows else rows[0]
        if not press_verified(emu, addr, 'up', nxt, 'pin up'):
            return False
    return False


def goto_index(emu, addr, rows, target_idx, labels):
    """闭环寻的: 每按一次 down/up 都校验钩子值; 值不符 ⇒ 交给调用方重钉顶。"""
    for _ in range(20):
        _, v = emu.sample(addr)
        if v not in rows:
            print('   !! 钩子值 %s 不在标定表 %s 里 (漂移)' % (v, rows), flush=True)
            return False
        idx = rows.index(v)
        if idx == target_idx:
            print('   ★ 已到达 idx=%d (%s), 钩子=%s' % (target_idx, labels[target_idx], v), flush=True)
            return True
        fwd = (target_idx - idx) % len(rows)
        back = (len(rows) - fwd) % len(rows)
        btn = 'down' if fwd <= back else 'up'
        step = 1 if btn == 'down' else -1
        nxt = rows[(idx + step) % len(rows)]
        print('   当前 idx=%d(%s) → 目标 idx=%d, 按 %s' %
              (idx, labels[idx], target_idx, btn), flush=True)
        if not press_verified(emu, addr, btn, nxt, '%s→idx%d' % (btn, (idx + step) % len(rows))):
            return False
    return False


def closed_loop(emu, addr, rows, labels, target_idx, stage):
    """钉顶 + 寻的, 失败则重钉顶重来。"""
    for attempt in range(1, MAX_REPIN + 1):
        print('   --- %s 尝试 %d/%d ---' % (stage, attempt, MAX_REPIN), flush=True)
        if not pin_top(emu, addr, rows):
            continue
        if goto_index(emu, addr, rows, target_idx, labels):
            return True
    return False


def flag_diff(before, after):
    """在监视区间里找"0→1"(新选中) 与 "1→0"(取消选中) 的字节偏移。返回 (sel, desel)。"""
    sel = [i for i in range(min(len(before), len(after)))
           if before[i] == 0 and after[i] == 1]
    desel = [i for i in range(min(len(before), len(after)))
             if before[i] == 1 and after[i] == 0]
    return sel, desel


def gold_band(path):
    """量左侧列表框里金色高亮带的中心 y (round60 口径: x 60..275, y 70..358)。"""
    from PIL import Image
    px = Image.open(path).convert('RGB').load()
    ys = []
    for y in range(70, 359):
        n = 0
        for x in range(60, 275):
            r, g, b = px[x, y]
            if r > 100 and 70 < g < 150 and b < 80 and r - b > 60:
                n += 1
        if n > 120:
            ys.append(y)
    if not ys:
        return None
    best, cur = [], [ys[0]]
    for y in ys[1:]:
        if y == cur[-1] + 1:
            cur.append(y)
        else:
            best = cur if len(cur) > len(best) else best
            cur = [y]
    best = cur if len(cur) > len(best) else best
    return (best[0] + best[-1]) / 2.0


def row_from_y(y):
    if y is None:
        return None
    for r, ry in SF_ROW_Y.items():
        if abs(y - ry) <= 13:
            return r
    return None


def snap_band(emu, name, tries=3, settle=200):
    """请求一张截图并量出金带 y → 行号 (渲染侧观测)。

    坑 (round61 踩过): 截图是 GS 线程异步写的 —— 文件刚出现时可能还在写, 或刚好抓到
    高亮条**滑动过程中**的帧。所以这里必须: ① 等 settle 帧让动画停下; ② 量不出带就
    **整张重拍**, 而不是立刻返回 None (第一版就是在这里误判成"up 未生效")。
    """
    for _t in range(tries):
        p = os.path.join(emu.dump, name + '.png')
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass
        emu.send('snap %s' % name)
        emu.wait_frame((emu.sample()[0] or 0) + settle)
        t0 = time.time()
        while time.time() - t0 < 10.0:
            if os.path.isfile(p):
                try:
                    y = gold_band(p)
                except Exception:                            # noqa: BLE001
                    y = None
                if y is not None:
                    return y, row_from_y(y)
            time.sleep(0.1)
    return None, None


def sf_press_down(emu, addr, cur_row, tag):
    """在特别收录列表里按一次 down, 并用**两种观测**验证"正好下移一行"。

    返回 (ok, new_row, note)。失败时不动 (由调用方决定重试/报错)。
    """
    fr0, before = emu.region(addr)
    emu.tap('down')
    emu.wait_frame((fr0 or 0) + 200)
    fr1, after = emu.region(addr)
    sel, desel = (flag_diff(before, after) if (before and after) else ([], []))
    mem_ok = (len(sel) == 1 and len(desel) == 1)
    y, row = snap_band(emu, '%s_probe' % tag)
    note = '内存标志 0→1@%s 1→0@%s (%s); 金带 y=%s → 行 %s' % (
        ['%04X' % i for i in sel], ['%04X' % i for i in desel],
        '恰好一对' if mem_ok else '未成对/区间不含', y, row)
    if row is None:
        return False, cur_row, note + ' [像素未识别]'
    if row == cur_row:
        return False, cur_row, note + ' [按了没动 = 丢键]'
    return True, row, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('version', help='work/builds 下的版本名, 如 GR_TEST_FONT2')
    ap.add_argument('--iso', default=None)
    ap.add_argument('--tag', default='hook1')
    ap.add_argument('--menu-addr', default=None)
    ap.add_argument('--sf-addr', default=None)
    ap.add_argument('--menu-target-idx', type=int, default=MENU_TARGET_IDX)
    ap.add_argument('--sf-target-idx', type=int, default=SF_TARGET_IDX)
    ap.add_argument('--maxframes', type=int, default=40000)
    ap.add_argument('--snap', type=int, default=500, help='周期截图间隔 (0=关)')
    ap.add_argument('--no-page-tries', action='store_true', help='到页后不试翻页键')
    ap.add_argument('--take-over', action='store_true',
                    help='★ 抢占模拟器: 检测到已有 pcsx2-gsrunner 在跑时把它杀掉再起。'
                         '默认**不杀**(实机单实例)—— 今天因无条件杀进程害过三个并行任务。')
    a = ap.parse_args()

    menu_addr = int(a.menu_addr, 0) if a.menu_addr else MENU_SEL_ADDR
    sf_addr = int(a.sf_addr, 0) if a.sf_addr else SF_SEL_ADDR
    if sf_addr is None or not SF_ROWS:
        sys.exit('缺少特别收录列表的标定 (SF_SEL_ADDR/SF_ROWS); 先跑 r61_recon2.py + r61_diff_rows.py')

    iso = os.path.abspath(a.iso or os.path.join(BUILDS, a.version, '%s.iso' % a.version))
    assert os.path.isfile(iso), 'ISO 不存在: %s' % iso
    temp = os.path.join(BUILDS, a.version, 'temp')
    os.makedirs(temp, exist_ok=True)
    dump = os.path.join(temp, 'dump_%s' % a.tag)
    cmd = os.path.join(temp, 'live_%s.txt' % a.tag)
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(os.path.join(dump, 'mc'))
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC, f), os.path.join(dump, 'mc', f))
    open(cmd, 'w').close()
    # 实机单实例 ---------------------------------------------------------------
    # ★ round70: 默认**不再杀别人的实例**。今天(10-14)因为这里无条件 Stop-Process,
    #   三个并行任务的抓帧被判成"残留"杀掉(9:47 / 10:10), 属典型友军火力。
    #   默认 = 检测到在跑就报错退出; 确要抢占才显式加 --take-over。
    _n = subprocess.run(['powershell', '-NoProfile', '-Command',
                         '@(Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue).Count'],
                        capture_output=True, text=True).stdout.strip()
    _n = int(_n) if _n.isdigit() else 0
    if _n > 0:
        if getattr(a, 'take_over', False):
            print('[warn] --take-over: 抢占模拟器, 杀掉 %d 个在跑的 pcsx2-gsrunner' % _n, flush=True)
            subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | '
                            'Stop-Process -Force'], capture_output=True)
            time.sleep(0.4)
        else:
            raise SystemExit(
                '!! 已有 %d 个 pcsx2-gsrunner 在跑 —— 实机单实例, 本工具默认不抢。\n'
                '   等对方跑完再试; 确要抢占请加 --take-over(会杀掉对方的实例)。' % _n)
    else:
        time.sleep(0.4)

    print('=' * 78)
    print('nav_hook.py  版本=%s' % a.version)
    print('  阶段A 主菜单 钩子=%08X 目标=%s' % (menu_addr, MENU_LABELS[a.menu_target_idx]))
    print('  阶段B 特别收录 钩子=%08X 目标=%s (idx=%d)' % (sf_addr, SF_LABELS[a.sf_target_idx],
                                                          a.sf_target_idx))
    print('ISO  = %s' % iso)
    print('dump = %s' % dump)
    print('=' * 78, flush=True)

    emu = Emu(iso, dump, cmd,
              [(menu_addr, 4, 1), (sf_addr, SF_SEL_SIZE, 1)], a.maxframes, a.snap)
    emu.start()
    print('pid = %d' % emu.proc.pid, flush=True)
    t0 = time.time()
    ok, reason = False, ''

    try:
        # ---- 阶段 1: 开环引导 (这段没有可用的状态钩子) ----
        print('\n[阶段1] 引导: start×10 → up×3 → cross (落点 = 主菜单)', flush=True)
        for f in BOOT_STARTS:
            emu.wait_frame(f)
            emu.tap('start')
        for f in BOOT_UPS:
            emu.wait_frame(f)
            emu.tap('up')
        emu.wait_frame(BOOT_CROSS)
        emu.tap('cross')

        # ---- 阶段 2: 握手, 等主菜单可交互 ----
        print('\n[阶段2] 握手: 按 up 看主菜单钩子是否跟着变', flush=True)
        emu.wait_frame(8000)
        hot = False
        for probe in range(8):
            f0, v0 = emu.sample(menu_addr)
            emu.tap('up')
            emu.wait_frame((f0 or 0) + 120)
            f1, v1 = emu.sample(menu_addr)
            print('   探测 #%d: 钩子 %s → %s' % (probe, v0, v1), flush=True)
            if v1 != v0 and v1 in MENU_ROWS:
                hot = True
                break
            emu.wait_frame((emu.sample()[0] or 0) + 800)
        if not hot:
            raise RuntimeError('主菜单钩子不响应 (菜单未激活?)')

        # ---- 阶段 3: 闭环走到「特别收录」并进入 ----
        print('\n[阶段3] 闭环: 主菜单 → 「特别收录」', flush=True)
        if not closed_loop(emu, menu_addr, MENU_ROWS, MENU_LABELS, a.menu_target_idx, '主菜单'):
            raise RuntimeError('主菜单闭环失败')
        _, v = emu.sample(menu_addr)
        print('   cross 进入 (钩子=%s 已复核)' % v, flush=True)
        emu.tap('cross')
        f_enter = emu.sample()[0] or 0

        # ---- 阶段 4: 等特别收录列表可交互, 再闭环走到「访谈」 ----
        print('\n[阶段4] 等特别收录列表激活, 再闭环到「访谈」(第 9 行)', flush=True)
        emu.wait_frame(f_enter + 3000)
        y0, row0 = snap_band(emu, 'sf_probe_a')
        hot = False
        for probe in range(10):
            fr0, _ = emu.sample()
            emu.tap('down')
            emu.wait_frame((fr0 or 0) + 250)
            y1, row1 = snap_band(emu, 'sf_probe_b')
            print('   探测 #%d: 金带 y=%s → %s (行 %s)' % (probe, y0, y1, row1), flush=True)
            if y1 is not None and y0 is not None and abs(y1 - y0) > 5:
                hot = True
                break
            emu.wait_frame((emu.sample()[0] or 0) + 1200)
            y0 = y1
        if not hot:
            raise RuntimeError('特别收录列表未进入可交互状态')
        # 回到列表顶: 列表是环形的, 不能靠"连按 up 钉顶"; 用**已验证的 down/up 计数**回第 1 行。
        # 先把当前行按像素找回来, 再一路 up 到第 1 行 (每步都验)。
        _, cur = snap_band(emu, 'sf_probe_c')
        if cur is None:
            raise RuntimeError('无法从像素识别当前行')
        print('   当前行 = %s' % cur, flush=True)
        for _ in range(12):
            if cur == 1:
                break
            fr0, before = emu.region(sf_addr)
            emu.tap('up')
            emu.wait_frame((fr0 or 0) + 200)
            _, nrow = snap_band(emu, 'sf_up_probe')     # snap_band 返回 (y, 行号)
            if nrow is None or nrow == cur:
                print('      up 未生效 (行 %s → %s), 重按一次' % (cur, nrow), flush=True)
                emu.tap('up')
                _, nrow = snap_band(emu, 'sf_up_probe2')
            if nrow is None or nrow == cur:
                raise RuntimeError('up 连续两次未生效 (当前行 %s → %s)' % (cur, nrow))
            cur = nrow
        if cur != 1:
            raise RuntimeError('未能回到第 1 行 (停在 %s)' % cur)
        print('   ★ 已确认在第 1 行「影片」(金带 y=%s)' % SF_ROW_Y[1], flush=True)

        target_row = SF_ROWS[a.sf_target_idx]
        print('   目标 = 第 %d 行「%s」; 需要 %d 次已验证的 down'
              % (target_row, SF_LABELS[a.sf_target_idx], target_row - cur), flush=True)
        steps = 0
        while cur != target_row and steps < 15:
            ok_step, nrow, note = sf_press_down(emu, sf_addr, cur, 'sf')
            steps += 1
            print('   down #%d: %s' % (steps, note), flush=True)
            emu.events.append((emu.sample()[0], cur, 'down -> %s' % nrow))
            if ok_step:
                cur = nrow
            else:
                # 丢键/重键: 重按一次; 若已越过目标, 用 up 回退一格 (同样验证)
                if nrow is not None and nrow != cur:
                    cur = nrow
                    continue
                print('      → 重按一次', flush=True)
                ok_step, nrow, note = sf_press_down(emu, sf_addr, cur, 'sf_retry')
                print('      重按: %s' % note, flush=True)
                if ok_step:
                    cur = nrow
                else:
                    raise RuntimeError('down 连续两次无效 (卡在第 %s 行)' % cur)
        if cur != target_row:
            raise RuntimeError('未到达第 %d 行 (停在 %s)' % (target_row, cur))
        print('   ★ 到达第 %d 行「%s」(两种观测一致)' % (cur, SF_LABELS[a.sf_target_idx]), flush=True)

        # ---- 阶段 5: 打开并取证 ----
        print('\n[阶段5] cross 打开「开发访谈 1」', flush=True)
        emu.tap('cross')
        f_arr = (emu.sample()[0] or 0) + 1500
        emu.wait_frame(f_arr)
        emu.send('drawwin %d %d' % (f_arr - 1200, f_arr + 1800))
        emu.send('snap %s_page' % a.tag)
        emu.wait_frame(f_arr + 260)
        emu.send('dump %s_page' % a.tag)
        if not a.no_page_tries:
            print('\n[阶段6] 页内试"翻页/滚动"键 (每键一张图)', flush=True)
            t = f_arr + 700
            for i, btn in enumerate(('down', 'down', 'right', 'l1', 'r1', 'left')):
                emu.wait_frame(t); emu.tap(btn)
                t += 500
                emu.wait_frame(t)
                emu.send('snap %s_pg%d_%s' % (a.tag, i, btn))
            emu.send('drawwin %d %d' % (t - 4000, t + 200))
        ok, reason = True, '到达「开发访谈 1」'
    except Exception as e:                                   # noqa: BLE001
        ok, reason = False, '%s: %s' % (type(e).__name__, e)
        print('\n!! 中断: %s' % reason, flush=True)
        try:
            emu.send('snap %s_last' % a.tag)
            emu.wait_frame((emu.sample()[0] or 0) + 120)
        except Exception:                                    # noqa: BLE001
            pass

    try:
        f, _ = emu.sample()
        if f is not None and f < a.maxframes - 60:
            print('\n[收尾] 主动停机 (F%s)' % f, flush=True)
            emu.proc.terminate()
    except Exception:                                        # noqa: BLE001
        pass
    try:
        emu.proc.wait(timeout=120)
    except Exception:                                        # noqa: BLE001
        emu.proc.kill()
    el = time.time() - t0

    seqp = os.path.join(dump, 'hook_sequence.txt')
    with open(seqp, 'w', encoding='utf-8') as fh:
        for fr, v, note in emu.events:
            fh.write('%s\t%s\t%s\n' % (fr, v, note))

    dl = os.path.join(dump, 'drawlog.txt')
    if os.path.isfile(dl):
        n_lines, n_text, samples, sites = 0, 0, [], {}
        for ln in io.open(dl, encoding='utf-8', errors='replace'):
            n_lines += 1
            m = re.match(r'F(\d+) PC=(\S+)', ln)
            if m:
                sites[m.group(2)] = sites.get(m.group(2), 0) + 1
            if '|' in ln:
                try:
                    b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
                except Exception:                            # noqa: BLE001
                    continue
                t = dec_bytes(b)
                if t:
                    n_text += 1
                    if len(samples) < 25:
                        samples.append('%s | %s' % (ln.split()[0], t))
        with open(os.path.join(dump, 'drawlog_summary.txt'), 'w', encoding='utf-8') as fh:
            fh.write('drawlog 行数 = %d, 含可解码文本的行 = %d\n' % (n_lines, n_text))
            fh.write('绘制站点计数 = %s\n\n' % json.dumps(sites, ensure_ascii=False))
            fh.write('文本样本 (前 25 条):\n')
            for s in samples:
                fh.write('  %s\n' % s)
        print('\ndrawlog: %d 行, 其中可解码文本 %d 行; 站点=%s' % (n_lines, n_text, sites), flush=True)

    print('\n' + '=' * 78)
    print('结果: %s — %s' % ('★ 成功到达' if ok else '✗ 失败', reason))
    print('耗时 = %.0f s' % el)
    shots = sorted(x for x in os.listdir(dump) if x.endswith('.png') and a.tag in x)
    print('截图 (%d 张): %s' % (len(shots), shots[:24]))
    print('钩子序列 = %s' % seqp)
    print('=' * 78, flush=True)
    return 0 if ok else 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
