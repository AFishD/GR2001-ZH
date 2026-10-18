# -*- coding: utf-8 -*-
r"""hashr_dump_font.py — 在 **K2 几何** (64 列 / SKIP=2 / Y0=3 / gate 0xBA) 上跑 dump_font 的包装器

    python work/builds/GR_HASHR/tools/hashr_dump_font.py --iso <iso> --out <dir> \
        [--charset <json>] [--no-png]

★ 为什么不能用 tools/re/toolbelt/fa_dump_font.py: 那个包装器只覆写 NCOL/LEAD_HI/PAIR_LEAD_HI ——
  它对应 FA2400 的 **SKIP=3 / Y0=2**; K2 改成了 **SKIP=2 / Y0=3** ⇒ 不覆写这两个会让
  row≥12 之后整体错一行 ⇒ 假"截断(丢行)"。本包装器把 5 个常量都覆写 (进程内, 不改文件)。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                          # noqa: E402

OLD = (tcslib.NCOL, tcslib.GRID_SKIP_ROWS, tcslib.GRID_Y0,
       tcslib.LEAD_HI, tcslib.PAIR_LEAD_HI)
tcslib.NCOL, tcslib.GRID_SKIP_ROWS, tcslib.GRID_Y0 = 64, 2, 3
tcslib.LEAD_HI = tcslib.PAIR_LEAD_HI = 0xBA
print('[wrap] tcslib 进程内覆写: NCOL %d→%d ; GRID_SKIP_ROWS %d→%d ; GRID_Y0 %d→%d ; '
      'LEAD_HI 0x%02X→0x%02X ; PAIR_LEAD_HI 0x%02X→0x%02X'
      % (OLD[0], tcslib.NCOL, OLD[1], tcslib.GRID_SKIP_ROWS, OLD[2], tcslib.GRID_Y0,
         OLD[3], tcslib.LEAD_HI, OLD[4], tcslib.PAIR_LEAD_HI), flush=True)
if '--charset' in sys.argv:
    i = sys.argv.index('--charset')
    tcslib.CHARSET = os.path.abspath(sys.argv[i + 1])
    tcslib.Charset.__init__.__defaults__ = (tcslib.CHARSET,)
    del sys.argv[i:i + 2]
    print('[wrap] charset 覆写为 %s' % tcslib.CHARSET, flush=True)
import dump_font                                                       # noqa: E402

sys.exit(dump_font.main())
