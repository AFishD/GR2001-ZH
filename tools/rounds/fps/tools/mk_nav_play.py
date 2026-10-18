# -*- coding: utf-8 -*-
r"""mk_nav_play.py -- generate the deterministic "real play" input table for the
GR_FPS A/B (2fps idle hang hunt).   ★ v2 = 按 probe 实测帧号校正过的版本。

Output: work/builds/GR_FPS/tools/nav_play.txt

格式 (见 third_party/emu/pcsx2_src/pcsx2-gsrunner/GRResearch.cpp ParseCommandLineArgs):
    <frame> <button> <tap|hold|release>
  * `tap`     -> 按下, 并在 fr+12 自动松开 (除非另有一行 release)
  * `release` -> 在 fr 松开
  * `hold`    -> 按下, 永不自动松开 (必须配一行 release)
  按钮名必须大写首字母, 取值来自 PadDualshock2 的绑定表:
    Up Down Left Right Triangle Circle Cross Square Select Start L1 L2 L3 R1 R2 R3

按键语义 (项目既有结论, docs/PROGRESS.md §46 + docs/REPORT_hook_nav.md):
  本作菜单**按住约 7 帧就开始连发** ⇒ `tap`(默认按住 12 帧)必然随机多走 2~3 项。
  正解 = `tap` + 紧跟一行 `release`(fr+2) 的 **2~3 帧短按** ⇒ 每次精确 ±1 项。
  本文件所有菜单按键都走这个 `short()` 形式。

★ 时间线 = 从 `zh113b_probe` 手臂的 658 张快照**逐张看图**反推出来的, 不是猜的:
    f00004020  主菜单, 高亮「战役」                        <- B/C 段生效
    f00006000  简报页「简介 / GR-M01」+ 继续按钮            <- cross@4700/5400 走到这里
    f00007800  小队设置「GR-M01」+ 开始按钮(高亮)            <- cross@6500 生效
    f00012900  ★ in-level 游玩 (HUD 正常)                  <- cross@11500..12700 按下「开始」
    f00012960..13020  黑屏 90 帧 (关卡切换/淡入)
    f00013200  暂停菜单: 继续 / 快速保存 / [灰项] / 重新开始 / 选项 / 退出  <- start@13200
    f00014010  暂停菜单, 高亮移到「快速保存」                <- down@14000 生效 (±1 项精确)
    f00015810  选项页 (被后面的 down/cross 带偏)
  ⇒ v2 把「开始」的确认提前到 f9000 (probe 里浪费了 7700..12900 在小队设置页),
    并把暂停菜单的导航改成「先 up×5 钉顶, 再 down×1 精确落『快速保存』」。

本文件全部帧号写死; 不用随机; 不依赖任何外部状态。
"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nav_play.txt')
L = []


def C(s):
    L.append('# ' + s)


def short(fr, btn, rel=2):
    """2~3 帧短按: 精确 ±1 项, 不触发连发。"""
    L.append('%d %s tap' % (fr, btn))
    L.append('%d %s release' % (fr + rel, btn))


def tap12(fr, btn):
    """`tap` 原义: 按下并在 fr+12 自动松开。"""
    L.append('%d %s tap' % (fr, btn))


def hold(fr, rel, btn):
    """长时间按住 (移动 / 持续开火)。"""
    L.append('%d %s hold' % (fr, btn))
    L.append('%d %s release' % (rel, btn))


# ================================================================ A 引导
C('=' * 72)
C('A. 跳过 logo / 宣传视频 / "Press START" (start 连打, 每 200 帧一次短按)')
C('=' * 72)
for f in range(800, 2603, 200):
    short(f, 'start')

# ================================================================ B 选择文件
C('')
C('=' * 72)
C('B. 「选择文件」: 初亮在「新建」, up x3 -> 档 1 (BASLUS-20613GHOST001); cross 载入')
C('=' * 72)
for f in (2850, 2950, 3050):
    short(f, 'up')
short(3250, 'cross', rel=22)      # 载入档案 (进盘读档, 给足 22 帧)

# ================================================================ C/D 主菜单 -> 战役 -> 关卡
C('')
C('=' * 72)
C('C. 主菜单: 光标默认在「训练」; down x2 -> 「战役」(probe f4020 实测高亮正确); cross 进入')
C('=' * 72)
short(3600, 'down')
short(3900, 'down')
short(4200, 'cross', rel=22)      # 进入「战役」
C('')
C('D. 战役 -> 简报页「简介 / GR-M01」 -> 小队设置 -> 开始 -> 关卡载入')
C('   依据 probe: cross@4700/5400 之后 f6000 已是简报页; cross@6500 之后 f7800 已是小队设置;')
C('   小队设置页上「开始」按钮本来就高亮 ⇒ 在 f9000 补一次 cross 即开始载入')
C('=' * 72)
short(4700, 'cross', rel=22)      # 战役 -> 简报页
short(6500, 'cross', rel=22)      # 简报页「继续/接受」 -> 小队设置
short(9000, 'cross', rel=22)      # 小队设置「开始」 -> 关卡载入
C('   (probe 实测: 关卡在「开始」之后约 1200~1400 帧进入 in-level)')

# ================================================================ E 游玩 + 射击
C('')
C('=' * 72)
C('E. in-level 游玩: 前进 + ★射击 (连按 R1 = 开火, 连按 cross)')
C('=' * 72)
hold(10600, 14200, 'up')          # 一直前进 (走路)
for f in (11000, 11500, 12000, 12500, 13000, 13500):
    tap12(f, 'r1')                # R1 = 开火 (项目已定案: bind 12 = PAD_R1)
for f in (13800, 14100, 14400):
    tap12(f, 'cross')             # 连按 cross
short(14600, 'left')
short(14850, 'right')
for f in (15100, 15400):
    tap12(f, 'r1')

# ================================================================ G 暂停 + 存/读档
C('')
C('=' * 72)
C('G. ★暂停菜单 (start) -> 存/读档')
C('   probe 实测菜单: 继续 / 快速保存 / [灰项=快速读取, 无存档时不可选] / 重新开始 / 选项 / 退出')
C('   光标初始位不确定 ⇒ 先 up x5 钉顶(钳位则稳在「继续」), 再 down x1 精确落到「快速保存」')
C('=' * 72)
short(16000, 'start', rel=3)      # 开暂停菜单
for i in range(5):
    short(16600 + i * 200, 'up')  # 钉顶
short(17800, 'down')              # 继续 -> 快速保存
short(18400, 'cross', rel=3)      # ★ 快速保存 (存)
short(19000, 'down')              # 快速保存 -> 快速读取 (存完若变可选)
short(19600, 'cross', rel=3)      # ★ 快速读取 (读); 若仍灰则光标不动/再存一次, 都无害
short(20200, 'up')                # 回到「继续」
short(20800, 'up')
short(21400, 'cross', rel=3)      # 继续 -> 回游玩 (若未选中「继续」则被忽略, 后面还有 start 兜底)
short(22000, 'start', rel=3)      # 兜底: start 也能开关暂停菜单

# ================================================================ F 小队页面候选键
C('')
C('=' * 72)
C('F. ★切换小队页面 —— 候选键扫描 (任务书要求试 select/start/三角 组合)')
C('   每个候选键独占 1200 帧窗口, 前后留白 ⇒ 可从截图逐一判定"这个键到底开了什么界面"')
C('=' * 72)
CAND = ['select', 'triangle', 'circle', 'square', 'l1', 'l2', 'r2', 'r3', 'l3', 'start']
WIN = 720
f = 23200
for k in CAND:
    C('--- 候选键 %s @ f%d (窗口 %d 帧 ≈ 12 s) ---' % (k.upper(), f, WIN))
    short(f, k, rel=3)
    f += WIN
C('--- 候选键扫描结束, 下一个可用帧 = f%d ---' % f)

# ================================================================ H 继续游玩
C('')
C('=' * 72)
C('H. 回到游玩: 前进 + 射击, 跑到帧预算末尾 (帧预算 32000)')
C('=' * 72)
hold(30600, 32000, 'up')
tap12(31000, 'r1')
short(31600, 'cross')
tap12(31800, 'r1')
LAST = 31800
C('--- 本表最后一条 = f%d (帧预算取 32000) ---' % LAST)


def main():
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(L) + '\n')
    n_ev = sum(1 for x in L if x and not x.startswith('#'))
    print('wrote %s' % OUT)
    print('lines=%d  input_events=%d  last_frame=%d' % (len(L), n_ev, LAST))


if __name__ == '__main__':
    main()
