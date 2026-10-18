# -*- coding: utf-8 -*-
r"""p23_crop_hintbar.py — round42: 从实机截图里把**底部按钮提示栏**抠出来放大 (证据图)

用途: 用户说「我见过有四个手柄按键加至少一个左右键」—— 先证明"玩家看到的那些图标"
      来自 UI 提示栏 (与本工程的文本码无关), 再看文本图标码渲染成什么。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image                                            # noqa: E402

SRC = sys.argv[1]
OUT = sys.argv[2]
BOX = [int(x) for x in sys.argv[3:7]]            # x0 y0 x1 y1
S = int(sys.argv[7]) if len(sys.argv) > 7 else 4
im = Image.open(SRC).convert('RGB')
print('%s %s → crop %s 放大 %dx' % (os.path.basename(SRC), im.size, BOX, S))
c = im.crop(tuple(BOX))
c.resize((c.width * S, c.height * S), Image.NEAREST).save(OUT)
print('→ %s (%dx%d)' % (OUT, c.width * S, c.height * S))
