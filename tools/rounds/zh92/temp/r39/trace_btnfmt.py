# -*- coding: utf-8 -*-
"""r39: 捕获 dump_text_csv.py 在 line 607 崩溃时的真实局部变量。

做法: 给 dump_text_csv 模块的 dump_sfxml 包一层, 打补丁把 T.BTN_FMT 换成
一个记录**每次调用实参类型**的代理 —— 这样就能看出到底是哪种实参导致了 int。
只读, 不改任何被检文件。
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                   # noqa: E402

REAL = T.BTN_FMT


class Fmt(str):
    """str 子类, 记录每次 % 运算的实参类型。"""
    calls = []

    def __mod__(self, other):
        Fmt.calls.append(type(other).__name__)
        return REAL.__mod__(other)


T.BTN_FMT = Fmt(REAL)

sys.argv = ['dump_text_csv.py',
            '--iso', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'),
            '--out', os.path.join(HERE, 'repro', 'Y_text.csv'),
            '--resources', 'SFXML', '--no-en']
try:
    runpy.run_path(os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
                   run_name='__main__')
except SystemExit as e:
    print('[SystemExit] %s' % e)
except Exception as e:                                               # noqa: BLE001
    import traceback
    traceback.print_exc()
print('\nBTN_FMT %% 实参类型统计: %r' % (sorted(set(Fmt.calls)),))
print('实参类型计数: %s' % {k: Fmt.calls.count(k) for k in set(Fmt.calls)})
