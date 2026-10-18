# -*- coding: utf-8 -*-
r"""mk_nav_play_v3.py -- v3: 修正 v2 在小队设置页"按错按钮"的缺陷, 真正进入关卡。

★ v2 的错在哪 (有截图证据):
  v2 在 f9000 补了一次 cross, 想让小队设置页的「开始」按钮生效; 但 v2 把 probe 里
  那段 `up hold 7700..12900` 删掉了 ⇒ **焦点仍停在列表第一项「全部取消分配」**,
  这一下 cross 把整队人马清空了 (截图 f15480/f16022/f18420: 队员全是「－空－」,
  「开始」变灰不可按), 之后 15480..23220 全卡在小队设置页, **一次都没进过关卡**。

★ v3 的做法 = **原样复用 probe 里被证明能进关卡的那段输入**(probe 的 f12600 是「载入中」,
  f12900 是 in-level):
      hold up 7700..12900            <- 长时间按住 up, 焦点最终落到「开始」(probe f12000 截图实测)
      r1  tap 9100/9500/9900/10300/10700/11100   (小队设置页里 R1 无副作用)
      cross tap 11500/11800/12100/12400/12700    <- 其中一下按到「开始」⇒ 关卡载入
      ~f13100 起 in-level
  然后才接真正的游玩 (前进/开火) 与暂停菜单存读档。

时间线 (帧预算 32000, 最后一条输入 f31700):
  A 800..2602   start x10                      跳过 logo / Press START
  B 2850/2950/3050 up, 3250 cross              选择文件 -> 档 1
  C 3600/3900 down, 4200 cross                 主菜单 -> 战役
  D 4700 cross, 6500 cross                     简报页 -> 小队设置
  D2 7700..12900 up hold + r1/cross 串         小队设置 -> 开始 -> 关卡载入 (probe 原配方)
  E 13400..17000 游玩: 前进 + 连按 R1(开火) + 连按 cross
  G 17400..23400 暂停菜单: 钉顶 -> down -> 快速保存 -> 快速读取 -> 继续
  F 24200..31400 小队页面候选键扫描 (10 键 x 720 帧)
  H 31600..31700 收尾射击
"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nav_play_v3.txt')
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
C('D. 战役 -> 简报页「简介/GR-M01」-> 小队设置')
C('=' * 72)
short(4700, 'cross', rel=22)
short(6500, 'cross', rel=22)

C('')
C('=' * 72)
C('D2. ★小队设置 -> 「开始」-> 关卡载入   (probe 原配方, 已证明可达 in-level)')
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
