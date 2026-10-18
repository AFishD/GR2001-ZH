# -*- coding: utf-8 -*-
"""r39: 在 dump_sfxml 抛异常时打印 marks / n_ctrl / text 的真实状态。只读。"""
import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def hook(tp, value, tb):
    if tb is None:
        return
    frames = []
    f = tb
    while f:
        frames.append(f)
        f = f.tb_next
    print('\n===== 崩溃现场 =====')
    for fr in frames:
        print('  文件 %s:%d  函数 %s' % (fr.tb_frame.f_code.co_filename.split('\\')[-1],
                                        fr.tb_lineno, fr.tb_frame.f_code.co_name))
    last = frames[-1].tb_frame
    for name in ('marks', 'n_ctrl', 'text', 'k', 'body', 'ln', 'off'):
        if name in last.f_locals:
            v = last.f_locals[name]
            print('  %-8s = %r  (type=%s)' % (name, v, type(v).__name__))
    sys.__excepthook__(tp, value, tb)


sys.excepthook = hook
sys.argv = ['dump_text_csv.py',
            '--iso', os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'),
            '--out', os.path.join(HERE, 'repro', 'W_text.csv'),
            '--resources', 'SFXML']
try:
    runpy.run_path(os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
                   run_name='__main__')
except SystemExit as e:
    print('[SystemExit] %s' % e)
