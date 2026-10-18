# -*- coding: utf-8 -*-
r"""gen_input.py — 生成"长时间游玩"确定性输入脚本 (格式: <frame> <btn> <tap|hold|release>)

设计要点
--------
* 引导段 (f800..f36502) **逐行抄** `work/builds/GR_FPS/tools/nav_play.txt` —— 那一段已被
  实机跑通到"关卡内可操作"(见 GR_FPS/out/zh113b_probe 的 658 张截图 & ANALYSIS.json),
  不要重新发明。
* 之后进入**动作循环**, 目标是持续 72,000+ 帧的"在关卡里动 + 打 + 换武器/看地图":
    · 移动: `up hold` 长按 + 定期 `release`, 中间穿插 left/right/down 转向与横移
    · 开火: r1 / r2 交替短按 (r1 = 主武器, 这也是 nav_play 已用的键)
    · 换武器/小队/地图: l1 / l2 / select / triangle / square / circle 轮转短按
    · 存读档: **只做一次** (f40000 附近) start → down → cross → start, 避免整局被
      "放弃任务"踢回主菜单 (那会把后面的帧全变成菜单 soak, 偏离"游玩中崩溃"的场景)。
* 所有 `hold` 都有配对的 `release`; 相邻事件至少隔 2 帧 (emulator 每帧只处理一次
  ProcessInput, 同帧事件顺序不可靠)。
"""
import argparse
import os

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'

# ---- 引导段: 逐行抄自 GR_FPS/tools/nav_play.txt (只保留按键行) ----
BOOT = """
800 start tap
1000 start tap
1200 start tap
1400 start tap
1600 start tap
1800 start tap
2000 start tap
2200 start tap
2400 start tap
2600 start tap
2850 up tap
2950 up tap
3050 up tap
3250 cross tap
3600 down tap
3900 down tap
4200 cross tap
4700 cross tap
5400 cross tap
6500 cross tap
7700 up hold
9100 r1 tap
9500 r1 tap
9900 r1 tap
10300 r1 tap
10700 r1 tap
11100 r1 tap
11500 cross tap
11800 cross tap
12100 cross tap
12400 cross tap
12700 cross tap
12900 up release
12950 left tap
13200 start tap
14000 down tap
14600 down tap
15200 down tap
15800 cross tap
16400 cross tap
17000 cross tap
17600 cross tap
18400 start tap
19400 select tap
20600 triangle tap
21800 circle tap
23000 square tap
24200 l1 tap
25400 l2 tap
26600 r2 tap
27800 r3 tap
29000 l3 tap
30200 start tap
31600 up hold
31800 r1 tap
32300 r1 tap
32800 r1 tap
33300 r1 tap
33800 r1 tap
34300 r1 tap
34600 up release
35000 cross tap
35500 cross tap
36000 r1 tap
36500 r1 tap
"""

# ---- 动作循环配方 ----
# (相对周期起点的帧偏移, 键, 动作)。周期 = CYCLE 帧。
PHASE_MOVE = [
    (0,    'up',       'hold'),      # 前进
    (300,  'r1',       'tap'),       # 开火 (主武器)
    (600,  'r1',       'tap'),
    (900,  'left',     'tap'),       # 左转/横移
    (1200, 'r1',       'tap'),
    (1500, 'right',    'tap'),       # 右转/横移
    (1800, 'r2',       'tap'),       # 副武器/换武器
    (2100, 'r1',       'tap'),
    (2400, 'l2',       'tap'),       # 小队/望远镜
    (2700, 'up',       'release'),   # 停一下再走 (避免一直顶到墙)
    (2850, 'down',     'hold'),      # 后退, 拉开距离
    (3300, 'r1',       'tap'),
    (3600, 'down',     'release'),
    (3750, 'cross',    'tap'),       # 动作/装弹/确认
    (4000, 'l1',       'tap'),       # 换武器/手雷
    (4200, 'select',   'tap'),       # 地图/战术视图
    (4500, 'select',   'tap'),       # 关闭
    (4700, 'triangle', 'tap'),       # 小队指令
    (5000, 'r1',       'tap'),
    (5300, 'square',   'tap'),       # 蹲/趴
    (5600, 'r1',       'tap'),
    (5900, 'square',   'tap'),       # 站起来
    (6100, 'circle',   'tap'),
    (6300, 'r1',       'tap'),
    (6600, 'up',       'hold'),      # 再前进
    (7200, 'r1',       'tap'),
    (7500, 'left',     'tap'),
    (7800, 'r1',       'tap'),
    (8100, 'right',    'tap'),
    (8400, 'r1',       'tap'),
    (8700, 'l2',       'tap'),
    (9000, 'r1',       'tap'),
    (9300, 'up',       'release'),
    (9500, 'down',     'tap'),
    (9700, 'cross',    'tap'),
    (9900, 'r1',       'tap'),
]
CYCLE = 10200                       # 一个周期 (≈170 s 游戏时间)

# 存读档段: 只做一次, 独占 1 个周期 (f47200.., 长度 3600 帧)
SAVELOAD_LEN = 3600
SAVELOAD = [
    (50,   'start', 'tap'),      # 暂停菜单
    (900,  'down',  'tap'),
    (1200, 'cross', 'tap'),      # 存/读档项
    (1700, 'cross', 'tap'),
    (2200, 'cross', 'tap'),
    (2700, 'cross', 'tap'),
    (3200, 'start', 'tap'),      # 关菜单
    (3500, 'select','tap'),      # 顺手开一次地图, 吃满窗口
]


def build(total_frames):
    frames = []                                          # (frame, btn, act)
    boot_frames = set()
    for ln in BOOT.strip().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        f, btn, act = ln.split()
        frames.append((int(f), btn, act))
        boot_frames.add(int(f))

    # 周期基址: 第 1 个周期整段让给"存读档"窗口, 其余全是动作循环。
    # ★ 必须整段让出 —— 否则存读档的按键会和同周期动作按键撞在同一帧上。
    start = 37000                                        # 动作循环起点
    bases, f, n = [], start, 0
    while f < total_frames:
        bases.append(f)
        f += CYCLE if n != 1 else SAVELOAD_LEN
        n += 1
    for i, base in enumerate(bases):
        if i == 1:
            for (o, b, a) in SAVELOAD:
                if base + o < total_frames:
                    frames.append((base + o, b, a))
            continue
        for (o, b, a) in PHASE_MOVE:
            fr = base + o
            if fr >= total_frames:
                break
            frames.append((fr, b, a))
    n = len(bases) - 1                                   # 动作循环数 (不含存读档窗口)
    frames.sort(key=lambda x: (x[0], 0 if x[2] == 'release' else 1))
    return frames, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--frames', type=int, default=76000)
    a = ap.parse_args()
    frames, ncyc = build(a.frames)
    # 校验: hold 必须配对 release; 末尾被 total_frames 截断的 hold 直接丢弃
    holds, drop = {}, set()
    for i, (f, b, act) in enumerate(frames):
        if act == 'hold':
            holds[b] = i
        elif act == 'release':
            assert b in holds, 'release 没有对应 hold: %s @%d' % (b, f)
            del holds[b]
    for b, i in holds.items():
        print('  [注意] 末帧截断导致 hold 未配对, 丢弃: %s @%d' % (b, frames[i][0]))
        drop.add(i)
    frames = [x for i, x in enumerate(frames) if i not in drop]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# 自动生成: gen_input.py --frames %d ; %d 个动作循环 ; 末帧 = %d\n'
                 % (a.frames, ncyc, frames[-1][0]))
        for (f, b, act) in frames:
            fh.write('%d %s %s\n' % (f, b, act))
    print('写出 %s : %d 行, %d 个动作循环, 末帧 = %d'
          % (a.out, len(frames), ncyc, frames[-1][0]))


if __name__ == '__main__':
    main()
