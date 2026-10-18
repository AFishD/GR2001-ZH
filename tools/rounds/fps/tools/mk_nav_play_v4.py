# -*- coding: utf-8 -*-
r"""mk_nav_play_v4.py -- v4 = v3 + 把 probe 里那次 f5400 的 cross 补回来。

★ 为什么 v3 没进关卡 (有截图证据):
  v3 的 D 段是 `cross@4200 / cross@4700 / cross@6500` —— **比 probe 少了一次 `cross@5400`**。
  probe(v1) 的 D 段是 `cross@4200 / 4700 / 5400 / 6500` 共四次。
  少这一次以后, 「战役 → 简报页 → 小队设置」的每一步都晚了一点,
  于是 `up hold 7700..12900` 这段窗口落在小队设置页的**不同焦点位置**上,
  f11500..12700 那五下 cross 全都没按到「开始」⇒ 整条 32000 帧都停在小队设置页
  (v3 截图 f14040 / f18000 / f24240 全是「小队设置 GR-M01」)。

★ v4 的做法 = **逐字复制 probe 的 D 段 (四次 cross) + D2 段 (up hold + r1/cross 串)**,
  这是**唯一被截图证明过能进关卡**的时序 (probe f12600 = 「载入中…」, f12900 = in-level HUD)。
  其余阶段 (E 游玩射击 / G 暂停存读档 / F 小队键扫描 / H 收尾) 与 v3 完全相同, 便于对账。

帧预算 32000, 最后一条输入 f31700。
"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nav_play_v4.txt')
L = []


def C(s):
    L.append('# ' + s)


def short(fr, btn, rel=2):
    L.append('%d %s tap' % (fr, btn))
    L.append('%d %s release' % (fr + rel, btn))


def tap12(fr, btn):
    L.append('%d %s tap' % (fr, btn))


def hold(fr, rel, btn):
    L.append('%d %s hold' % (fr, btn))
    L.append('%d %s release' % (rel, btn))


C('=' * 72)
C('A. 跳过 logo / 宣传视频 / "Press START"')
C('=' * 72)
for f in range(800, 2603, 200):
    short(f, 'start')

C('')
C('=' * 72)
C('B. 「选择文件」: up x3 -> 档 1 (BASLUS-20613GHOST001); cross 载入')
C('=' * 72)
for f in (2850, 2950, 3050):
    short(f, 'up')
short(3250, 'cross', rel=22)

C('')
C('=' * 72)
C('C. 主菜单: down x2 -> 「战役」; cross 进入')
C('=' * 72)
short(3600, 'down')
short(3900, 'down')
short(4200, 'cross', rel=22)

C('')
C('=' * 72)
C('D. 战役 -> 简报页 -> 小队设置   ★ 四次 cross, 与 probe 逐字相同 (v3 少了 f5400 那次)')
C('=' * 72)
short(4700, 'cross', rel=22)
short(5400, 'cross', rel=22)      # ★ v3 缺的就是这一下
short(6500, 'cross', rel=22)

C('')
C('=' * 72)
C('D2. ★小队设置 -> 「开始」-> 关卡载入   (probe 原配方, 已被截图证明可达 in-level)')
C('=' * 72)
hold(7700, 12900, 'up')
for f in (9100, 9500, 9900, 10300, 10700, 11100):
    tap12(f, 'r1')
for f in (11500, 11800, 12100, 12400, 12700):
    tap12(f, 'cross')
C('   (probe 实测: f12600 = 「载入中…」, f12900 = in-level, HUD 正常)')

C('')
C('=' * 72)
C('E. ★in-level 游玩: 前进 + 连按 R1 (开火) + 连按 cross')
C('=' * 72)
hold(13400, 16400, 'up')
for f in (13800, 14200, 14600, 15000, 15400, 15800):
    tap12(f, 'r1')
for f in (16000, 16200, 16400):
    tap12(f, 'cross')
short(16600, 'left')
short(16800, 'right')
for f in (17000, 17300):
    tap12(f, 'r1')

C('')
C('=' * 72)
C('G. ★暂停菜单 (start) -> 存/读档')
C('   菜单: 继续 / 快速保存 / [灰项 快速读取] / 重新开始 / 选项 / 退出')
C('=' * 72)
short(17600, 'start', rel=3)
for i in range(5):
    short(18200 + i * 200, 'up')
short(19400, 'down')
short(20000, 'cross', rel=3)
short(20600, 'down')
short(21200, 'cross', rel=3)
short(21800, 'up')
short(22200, 'up')
short(22600, 'cross', rel=3)
short(23200, 'start', rel=3)

C('')
C('=' * 72)
C('F. ★切换小队页面 —— 候选键扫描 (select/triangle/circle/square/l1/l2/r2/r3/l3/start)')
C('=' * 72)
CAND = ['select', 'triangle', 'circle', 'square', 'l1', 'l2', 'r2', 'r3', 'l3', 'start']
WIN = 720
f = 24200
for k in CAND:
    C('--- 候选键 %s @ f%d (窗口 %d 帧) ---' % (k.upper(), f, WIN))
    short(f, k, rel=3)
    f += WIN

C('')
C('=' * 72)
C('H. 收尾: 继续前进 + 射击')
C('=' * 72)
hold(31600, 32000, 'up')
tap12(31700, 'r1')
LAST = 31700
C('--- 本表最后一条 = f%d (帧预算取 32000) ---' % LAST)


def main():
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(L) + '\n')
    n_ev = sum(1 for x in L if x and not x.startswith('#'))
    print('wrote %s' % OUT)
    print('lines=%d  input_events=%d  last_frame=%d' % (len(L), n_ev, LAST))


if __name__ == '__main__':
    main()
