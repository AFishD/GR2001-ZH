# -*- coding: utf-8 -*-
r"""r49_ab_all.py — round49 实机 A/B 驱动: 按同一份 nav 依次跑 **两盘** (单实例守规)。

每轮之间: cap_run.py 自己会等"连续 2 次、间隔 30s 无任何 pcsx2-gsrunner"; 记忆卡每轮从
`third_party/emu/run/memcards` 模板复位到独占目录 (与 tools/capture/run_opt.py 同一套口径)。

用法:
  python r49_ab_all.py menu        # 只跑主菜单那一对 (最先验证管线)
  python r49_ab_all.py rest        # 跑 doc + weapon 两对
  python r49_ab_all.py all
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
ISO97 = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
ISO98 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

RUNS = [
    ('menu', 'r49_menu_zh97', ISO97, 'r49_nav_menu.txt', 13000, '战术演习'),
    ('menu', 'r49_menu_zh98', ISO98, 'r49_nav_menu.txt', 13000, '战术演习'),
    ('doc', 'r49_doc_zh97', ISO97, 'r49_nav_doc.txt', 30200, '何为幽灵'),
    ('doc', 'r49_doc_zh98', ISO98, 'r49_nav_doc.txt', 30200, '何为幽灵'),
    ('wpn', 'r49_wpn_zh97', ISO97, 'r49_nav_weapon.txt', 30500, '手枪'),
    ('wpn', 'r49_wpn_zh98', ISO98, 'r49_nav_weapon.txt', 30500, '手枪'),
]


def main():
    which = sys.argv[1:] or ['all']
    if 'rest' in which:
        which = ['doc', 'wpn']
    for (grp, tag, iso, nav, frames, req) in RUNS:
        if 'all' not in which and grp not in which:
            continue
        cmd = [sys.executable, os.path.join(HERE, 'cap_run.py'),
               '--iso', iso, '--dump', os.path.join(HERE, tag),
               '--nav', os.path.join(HERE, nav), '--frames', str(frames),
               '--tag', tag, '--require', req]
        print('=' * 78)
        print('[ab] %s  frames=%d  iso=%s' % (tag, frames, os.path.basename(iso)))
        t0 = time.time()
        r = subprocess.run(cmd, cwd=HERE)
        print('[ab] %s rc=%s 用时 %.0fs' % (tag, r.returncode, time.time() - t0))
    print('[ab] 全部结束')


if __name__ == '__main__':
    main()
