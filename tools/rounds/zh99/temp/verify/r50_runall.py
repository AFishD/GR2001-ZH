# -*- coding: utf-8 -*-
r"""r50_runall.py - round50 实机 A/B (最终版): 同一 nav 跑 GR_ZH98(前) 与 GR_ZH99(后), 逐帧逐像素比。

* GR_ZH98 侧抓帧**复用**上一批 (dump_r50_*_zh98) -- 同一张盘/同一份 nav/同一台模拟器;
  round49 已用同口径证明抓帧确定性 (GR_ZH97 vs GR_ZH98: 127/127, 302/302, 299/299 全等)。
* 本脚本只跑 GR_ZH99 侧。
铁律: 单实例 (r50_cap.py 内 wait_free) / 记忆卡每轮模板复位 / 按键 tap+release 短按 / 串行。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PY = sys.executable
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUNS = [('menu', 13000), ('weapon', 30500), ('doc', 30200)]


def main():
    only = sys.argv[1:] or None
    for (nav, frames) in RUNS:
        if only and nav not in only:
            continue
        tag = 'r50_%s_zh99' % nav
        env = dict(os.environ)
        env['R50_CHARSET'] = os.path.join(HERE, 'charset_zh99.json')
        cmd = [PY, os.path.join(HERE, 'r50_cap.py'),
               '--iso', os.path.join(REPO, 'work/builds/GR_ZH99/GR_ZH99.iso'),
               '--dump', os.path.join(HERE, 'dump_' + tag),
               '--nav', os.path.join(HERE, 'nav_%s.txt' % nav),
               '--frames', str(frames), '--snap', '100', '--tag', tag]
        print('=' * 70)
        print('[run] %s nav=%s frames=%d' % (tag, nav, frames), flush=True)
        r = subprocess.run(cmd, cwd=REPO, env=env)
        print('[run] %s 结束 rc=%s' % (tag, r.returncode), flush=True)
    print('[all] 结束', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
