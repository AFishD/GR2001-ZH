# -*- coding: utf-8 -*-
r"""r61_recon2.py — 第二轮侦察: 用**主菜单钩子**闭环进入「特别收录」, 再对特别收录列表逐行采样。

第一轮 (r61_recon.py) 的教训
---------------------------
nav_sf_interview.txt 的时间线在 `-grinputlive` (3 帧短按) 下**没能进入「特别收录」**:
9 个采样点全部落在**主菜单**上 (肉眼确认见 dump_recon/r61_rows_sheet.png)。
⇒ 第一轮的差分给出的是**主菜单选中项**变量, 不是特别收录列表的。

本轮流程 (全程可校验)
--------------------
  ① 引导: start×10 → up×3 → cross (与上一轮同; 这一段落点是主菜单)
  ② **握手**: 按 up, 看主菜单钩子 (0x013379D0) 是否跟着变 ⇒ 菜单是否已可交互
  ③ **闭环**: 钉顶 (钩子=1 训练) → 逐级校验走到「特别收录」(钩子=7) → cross 进入
  ④ 特别收录列表: 逐行 dump 全 EE RAM + 截图 (第 7 行「专家」是灰条, 光标跳过)
  ⑤ 回到「访谈」(第 9 行) → cross 打开「开发访谈 1」→ 抓图 + 开 drawlog 窗口 + dump

产物: dump_recon2/{sf_row*.png, sf_row*_f*_eeram.bin, memwatch.bin, drawlog.txt, grlog.txt}
      + recon2_stdout.log (钩子值序列)

用法: python work/builds/GR_ZH98/temp/r61/r61_recon2.py <iso> [maxframes]
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'capture'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import nav_hook as NH                                                    # noqa: E402

WORK = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r61')
GS = NH.GS

# ---- 主菜单标定 (round61 第一轮实测: 0x013379D0 = 1-based 项号, 灰条 #4 跳过) ----
MENU_ADDR = 0x013379D0
MENU_ROWS = [1, 2, 3, 5, 6, 7, 8, 9]          # 训练/战术演习/战役/多人游戏/统计/特别收录/选项/制作组
SF_MENU_IDX = 5                                # 「特别收录」在 MENU_ROWS 里的下标


def main():
    iso = os.path.abspath(sys.argv[1])
    maxframes = int(sys.argv[2]) if len(sys.argv) > 2 else 34000
    tag = 'recon2'
    dump = os.path.join(WORK, 'dump_' + tag)
    cmd = os.path.join(WORK, 'live_%s.txt' % tag)
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(os.path.join(dump, 'mc'))
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(NH.MC, f), os.path.join(dump, 'mc', f))
    open(cmd, 'w').close()
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Get-Process pcsx2-gsrunner -ErrorAction SilentlyContinue | Stop-Process -Force'],
                   capture_output=True)
    time.sleep(0.4)
    print('ISO = %s\ndump = %s' % (iso, dump), flush=True)

    emu = NH.Emu(iso, dump, cmd, [(MENU_ADDR, 4, 1)], maxframes, 200)
    emu.start()
    print('pid = %d' % emu.proc.pid, flush=True)
    t0 = time.time()

    def log(txt):
        f, v = emu.sample()
        print('   [F%-7s 主菜单钩子=%-4s] %s' % (f, v, txt), flush=True)

    # ---------- ① 引导 ----------
    for f in NH.BOOT_STARTS:
        emu.wait_frame(f)
        emu.tap('start')
    for f in NH.BOOT_UPS:
        emu.wait_frame(f)
        emu.tap('up')
    emu.wait_frame(NH.BOOT_CROSS)
    emu.tap('cross')
    print('\n[①] 引导完成 (start×10 → up×3 → cross)', flush=True)

    # ---------- ② 握手: 菜单是否已可交互 ----------
    print('\n[②] 握手: 按 up 看钩子是否跟着变', flush=True)
    emu.wait_frame(8000)
    interactive = False
    for probe in range(6):
        f0, v0 = emu.sample()
        log('握手探测 #%d 前' % probe)
        emu.tap('up')
        try:
            emu.wait_frame((f0 or 0) + 120)
        except Exception:                                        # noqa: BLE001
            break
        f1, v1 = emu.sample()
        print('        探测后 钩子=%s (前=%s)' % (v1, v0), flush=True)
        if v1 != v0 and v1 in MENU_ROWS:
            interactive = True
            break
    if not interactive:
        print('   !! 握手失败: 主菜单钩子不响应; 终止', flush=True)
        emu.proc.terminate()
        return 3
    print('   OK 主菜单可交互, 当前钩子=%s' % emu.sample()[1], flush=True)

    # ---------- ③ 闭环走到「特别收录」 ----------
    print('\n[③] 闭环: 钉顶 → 走到「特别收录」(钩子=7)', flush=True)
    ok = False
    for attempt in range(3):
        if not NH.pin_top(emu, MENU_ADDR, MENU_ROWS):
            print('   钉顶失败, 重试', flush=True)
            continue
        if NH.goto_index(emu, MENU_ADDR, MENU_ROWS, SF_MENU_IDX, NH.MENU_LABELS):
            ok = True
            break
    if not ok:
        print('   !! 未能走到「特别收录」; 终止', flush=True)
        emu.proc.terminate()
        return 4
    log('已选中「特别收录」, 按 cross 进入')
    emu.tap('cross')
    f_enter = emu.sample()[0]
    print('   cross 于 F%s' % f_enter, flush=True)

    # ---------- ④ 特别收录列表逐行采样 ----------
    # 列表开场动画长度未知 ⇒ 先用**像素级握手**确认它已可交互 (金带 y 会跟着 down 变)。
    import r61_check_rows as CR                                          # noqa: E402
    from PIL import Image                                                # noqa: E402

    def probe_band(name):
        p = os.path.join(dump, name + '.png')
        if os.path.isfile(p):
            os.remove(p)
        emu.send('snap %s' % name)
        emu.wait_frame((emu.sample()[0] or 0) + 120)
        for _ in range(80):
            if os.path.isfile(p):
                try:
                    return CR.gold_band(Image.open(p))
                except Exception:                                    # noqa: BLE001
                    pass
            time.sleep(0.1)
        return (None, 0)

    print('\n[④] 特别收录列表: 像素握手确认可交互', flush=True)
    t = (f_enter or 0) + 3000
    emu.wait_frame(t)
    interactive = False
    for probe in range(9):
        y0, _ = probe_band('sf_probe_a')
        t = (emu.sample()[0] or t) + 200
        emu.wait_frame(t)
        emu.tap('down')
        t += 400
        emu.wait_frame(t)
        y1, _ = probe_band('sf_probe_b')
        print('   握手 #%d: down 前金带 y=%s → 后 y=%s' % (probe, y0, y1), flush=True)
        if y0 is not None and y1 is not None and abs(y1 - y0) > 5:
            interactive = True
            break
        t += 1500
    if not interactive:
        print('   !! 特别收录列表始终未进入可交互状态; 终止', flush=True)
        emu.proc.terminate()
        return 5
    emu.tap('up')                     # 退回第 1 行
    t = (emu.sample()[0] or t) + 500
    emu.wait_frame(t)
    y, _ = probe_band('sf_probe_c')
    print('   回到第 1 行: 金带 y=%s' % y, flush=True)

    print('\n[④] 逐行采样 (每行 dump + snap)', flush=True)
    for k in range(9):
        if k > 0:
            t += 500
            emu.wait_frame(t)
            emu.tap('down')
        t += 500
        emu.wait_frame(t)
        f, v = emu.sample()
        print('   [F%-7s 主菜单钩子=%-4s] dump/snap sf_row%02d' % (f, v, k), flush=True)
        emu.send('dump sf_row%02d' % k)
        emu.send('snap sf_row%02d' % k)
        emu.wait_frame(t + 300)
    # ---------- ⑤ 回到「访谈」(第 9 行) 并打开 ----------
    t += 500
    emu.wait_frame(t)
    emu.tap('up')                          # 第 10 行 → 第 9 行
    t += 500
    emu.wait_frame(t)
    log('回到「访谈」(第 9 行)')
    emu.send('dump sf_row_interview')
    emu.send('snap sf_row_interview')
    emu.wait_frame(t + 300)
    t += 500
    emu.wait_frame(t)
    emu.tap('cross')
    f_page = t + 1500
    emu.wait_frame(f_page)
    log('已 cross 打开「开发访谈 1」')
    emu.send('drawwin %d %d' % (f_page - 1200, f_page + 1800))
    emu.send('snap page_interview')
    emu.wait_frame(f_page + 300)
    emu.send('dump page_interview')
    emu.wait_frame(f_page + 600)
    emu.send('snap page_interview_settled')
    print('\n[⑤] 取证完成, 停机', flush=True)

    emu.proc.terminate()
    try:
        emu.proc.wait(timeout=120)
    except Exception:                                            # noqa: BLE001
        emu.proc.kill()

    seqp = os.path.join(dump, 'hook_sequence.txt')
    with open(seqp, 'w', encoding='utf-8') as fh:
        for fr, v, note in emu.events:
            fh.write('%s\t%s\t%s\n' % (fr, v, note))
    print('耗时 = %.0f s; 钩子序列 = %s' % (time.time() - t0, seqp))
    return 0


if __name__ == '__main__':
    sys.exit(main())
