# -*- coding: utf-8 -*-
r"""ab_pair.py — 用指定 nav 跑一个盘的抓帧, 并用 drawlog 判定"到的是哪一页"; 不对就重跑。

用法:
  python ab_pair.py --iso <盘> --dump <名字> --nav <nav文件> --frames 14000
                    [--require 何为幽灵] [--tries 3]

要点:
  · `-grdrawwin 4000 <frames>` 让模拟器把**每帧绘制文本**写进 drawlog (运行中被独占锁定,
    只能在进程结束后读) ⇒ 跑完立刻解析, 判定页面与"哪些受影响字被画出来过";
  · 命中 --require 才保留该 dump; 否则同一份 nav 再跑 (每次按键登记次数有 ±1 抖动,
    重跑等于重新抽一次) —— 最多 --tries 次。
"""
import io
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab_run                                                       # noqa: E402

REPO = ab_run.REPO
AB = ab_run.AB
GS = ab_run.GS
MC_TPL = ab_run.MC_TPL


def main():
    a = sys.argv[1:]
    iso = a[a.index('--iso') + 1]
    dump = a[a.index('--dump') + 1]
    nav = a[a.index('--nav') + 1]
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 14000
    require = a[a.index('--require') + 1] if '--require' in a else None
    tries = int(a[a.index('--tries') + 1]) if '--tries' in a else 3
    if not os.path.isabs(dump):
        dump = os.path.join(AB, dump)
    if not os.path.isabs(nav):
        nav = os.path.join(REPO, 'tools', 'capture', nav) if not os.path.isfile(nav) else nav
    assert os.path.isfile(iso), iso
    assert os.path.isfile(nav), nav
    for t in range(1, tries + 1):
        ab_run.wait_free('%s try%d' % (os.path.basename(dump), t))
        os.makedirs(dump, exist_ok=True)
        mc = os.path.join(AB, 'mc_%s' % os.path.basename(dump))
        os.makedirs(mc, exist_ok=True)
        for f in ('Mcd001.ps2', 'Mcd002.ps2'):
            shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))
        args = [GS, '-grdumpdir', dump, '-grdrawwin', '4000', str(frames),
                '-grscanframes', '2000', '-grsnap', '100', '-grmaxframes', str(frames),
                '-grmemcards', mc, '-grinput', nav, '-renderer', 'dx11', '--', iso]
        ab_run.log('%s try%d: 启动 (nav=%s frames=%d)'
                   % (os.path.basename(dump), t, os.path.basename(nav), frames))
        t0 = time.time()
        with io.open(os.path.join(AB, 'pair_%s.log' % os.path.basename(dump)), 'a',
                     encoding='utf-8', newline='\n') as f:
            f.write('--- try%d 启动 %s frames=%d ---\n' % (t, nav, frames))
            f.flush()
            subprocess.run(args, cwd=os.path.dirname(GS), stdout=f, stderr=subprocess.STDOUT)
        n = len([x for x in os.listdir(dump) if x.startswith('snap_')])
        ab_run.log('%s try%d: 结束 用时%.0fs 帧数=%d' % (os.path.basename(dump), t,
                                                        time.time() - t0, n))
        dl = os.path.join(dump, 'drawlog.txt')
        lastf, texts = ab_run.tail_texts(dl, maxbytes=10 ** 9)
        pages = ab_run.classify(texts)
        blob = '\x00'.join(texts)
        chars = [c for c in '中斗训习面务准可会出换下如以到定是任' if c in blob]
        ab_run.log('   页面判定=%s; 出现过的受影响字=%s; 末帧=%d' % (pages, chars, lastf))
        if require is not None:
            good = require in blob
        else:
            good = ab_run.hit(texts)          # 默认要求 = 目标长文页特征 (ab_run.TARGET)
        if good:
            ab_run.log('★ 保留 dump=%s (require=%r)' % (dump, require))
            return
        ab_run.log('   ✗ 未命中 (require=%r) ⇒ 重跑' % require)
    ab_run.log('!! %s 试满 %d 次仍未命中 %r' % (dump, tries, require))


if __name__ == '__main__':
    main()
