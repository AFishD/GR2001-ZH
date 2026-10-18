# -*- coding: utf-8 -*-
r"""r60b_make_nav.py — 用 r49 验证过的时序重建"特别收录 → 访谈 → 第一篇"导航

r49_nav_doc.txt 的关键时序 (round49/51 实机到过特别收录内页):
  800..2600 : start x10   (跳过 logo/宣传视频/Press START)
  2850..3050: up x3       (主菜单上移)
  3250      : cross       (进入特别收录)
  10600..   : 列表内按键 (间隔 400 帧)
本脚本: 抄 r49 的前半段, 后半段改成"钉顶(up x9) → down x7 → cross"。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'temp', 'r49', 'nav', 'r49_nav_doc.txt')
DST = os.path.join(REPO, 'tools', 'capture', 'nav_sf_interview.txt')

lines = io.open(SRC, encoding='utf-8', errors='replace').read().splitlines()
# 取到 3250 的 cross release 为止 (含)
head = []
for ln in lines:
    head.append(ln)
    if ln.strip().startswith('3272 cross release'):
        break
print('抄 r49 前半段: %d 行 (到 3272 cross release)' % len(head))

out = [
    '# nav_sf_interview.txt — 主菜单 → 特别收录 → 倒数第二个「访谈」→ 打开第一篇「开发访谈 1」',
    '# ★ round60 重建: 时序抄 r49_nav_doc.txt (实机验证过到特别收录内页), 只改后半段。',
    '#   前半段: start x10 跳片头 → up x3 → cross 进特别收录 → 等 122 秒开场动画',
    '#   后半段: 列表内 up x9 钉顶 → down x7 到「访谈」(第 9 行; 第 7 行是灰条自动跳过) → cross 打开',
    '#   实测教训: 按键太早会被片头影片吃掉 (上一版就卡在片头); 间隔取 500 帧更稳。',
    '#   判据: 标题栏 = 「开发访谈 1」; 正文首行 = 「字库测试页 全 1285 字 · 每行 N 字」。',
]
out += head[1:]                     # 去掉 r49 的第一行注释, 其余照抄
f = 10600
for _ in range(9):                  # 钉顶
    out += ['%d up tap' % f, '%d up release' % (f + 2)]
    f += 500
f += 500
for _ in range(7):                  # 下移到「访谈」
    out += ['%d down tap' % f, '%d down release' % (f + 2)]
    f += 500
f += 700
out += ['%d cross tap' % f, '%d cross release' % (f + 2)]
# 打开后不动, 让正文停在画面里 (帧预算 30200 ≈ 503 s)

io.open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('写出 %s: %d 行; 末尾 8 行:' % (DST, len(out)))
for ln in out[-8:]:
    print('   ', ln)
