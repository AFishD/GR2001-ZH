# -*- coding: utf-8 -*-
r"""fix_release94.py — 给 GR_ZH94 资料包补齐人工维护的说明文件 (从 GR_ZH93 版替换版本号/ sha 后复制)"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OLD, NEW = 'GR_ZH93', 'GR_ZH94'
OLD_SHA = 'e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be'
NEW_SHA = '1cac50c1c7a6c827da006bdd09ce1214dc59b00493c7ce9e17495c2ac0d4f301'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

src = os.path.join(REPO, 'work', 'builds', OLD, 'release')
dst = os.path.join(REPO, 'work', 'builds', NEW, 'release')

for rel in ('README.md', os.path.join('text', 'README_文本表.md')):
    s, d = os.path.join(src, rel), os.path.join(dst, rel)
    if not os.path.isfile(s):
        print('[skip] 源不存在: %s' % rel)
        continue
    t = io.open(s, encoding='utf-8').read()
    n = t.count(OLD) + t.count(OLD_SHA)
    t = t.replace(OLD, NEW).replace(OLD_SHA, NEW_SHA)
    io.open(d, 'w', encoding='utf-8', newline='\n').write(t)
    print('[ok] %s (替换 %d 处版本号/sha)' % (rel, n))

# 追加一句本轮变化说明
rd = os.path.join(dst, 'README.md')
if os.path.isfile(rd):
    t = io.open(rd, encoding='utf-8').read()
    if '字形对齐' not in t:
        t += ('\n## 本轮变化 (GR_ZH94)\n\n'
              '- **修好了 181 个字形错位**（网格行 19..23 的字形原本不在引擎采样格上，'
              '游戏里会显示成同排另一个字）。实机 A/B 已闭环。\n'
              '- 38 个字的**内部码位**改派（你的文案一个字未改）。\n'
              '- 字库空位随之变化：**可直接用 34 个**（原 45）、需回收 151 个（原 140）。\n'
              '- 文案与 GR_ZH93 **逐字节相同**（2261 条 / 65271 字符，修改 0 条）。\n')
        io.open(rd, 'w', encoding='utf-8', newline='\n').write(t)
        print('[ok] README 追加本轮变化说明')
print('done')
