# -*- coding: utf-8 -*-
r"""fa_dump_font.py — 在**新几何盘** (64 列 / gate 0xBA) 上跑 dump_font 的包装器

    python tools/re/toolbelt/fa_dump_font.py --iso work/builds/GR_FA2400/GR_FA2400.iso --out <dir> [--grid]

★ 为什么需要包装器 (而不是直接改 tcslib):
  `tools/text_csv/tcslib.py` 的几何/闸门常量是**单值**的 (`NCOL=62` / `LEAD_HI=0xB5`),
  那是历史盘 (62 列、gate ≤ 0xB5) 的口径, 且 `tools/text_csv/**` 不在本轮写入范围。
  本包装器只在**进程内**覆写这 3 个常量, 然后调用未修改的 dump_font:
      tcslib.NCOL        = 64      ← 网格列数
      tcslib.LEAD_HI     = 0xBA    ← decode 的 lead 上界 (= gate)
      tcslib.PAIR_LEAD_HI= 0xBA    ← 允许写出的 pair lead 上界
  ⇒ **不改任何文件**, 也不影响其它盘 (各自进程各自口径)。
  工具链的永久同步 (把常量改成随盘读 ELF) 建议单开一轮 —— 见 docs/CAPACITY_2400.md「未达成项」。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                          # noqa: E402

OLD = (tcslib.NCOL, tcslib.LEAD_HI, tcslib.PAIR_LEAD_HI)
tcslib.NCOL, tcslib.LEAD_HI, tcslib.PAIR_LEAD_HI = 64, 0xBA, 0xBA
print('[wrap] tcslib 常量在**本进程内**覆写: NCOL %d→%d ; LEAD_HI 0x%02X→0x%02X ; '
      'PAIR_LEAD_HI 0x%02X→0x%02X (未改任何文件)'
      % (OLD[0], tcslib.NCOL, OLD[1], tcslib.LEAD_HI, OLD[2], tcslib.PAIR_LEAD_HI), flush=True)
if '--charset' in sys.argv:                     # ★ 用指定的 charset 副本跑 (取证: live 1877 口径)
    i = sys.argv.index('--charset')
    tcslib.CHARSET = os.path.abspath(sys.argv[i + 1])
    # ★ Charset.__init__ 的默认参数在**导入时**就绑定了旧路径 ⇒ 必须同时改 __defaults__
    tcslib.Charset.__init__.__defaults__ = (tcslib.CHARSET,)
    del sys.argv[i:i + 2]
    print('[wrap] charset 覆写为 %s' % tcslib.CHARSET, flush=True)
import dump_font                                                       # noqa: E402

sys.exit(dump_font.main())
