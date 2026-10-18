# -*- coding: utf-8 -*-
r"""spinfix_cave.py —— 【GR_SPINFIX】cave 选址：直接复用 GR_OOMFIX 的 oomfix_cave.py（已审计），
只把 FORBIDDEN 扩展为「本工程全部已知占用区 + GR_OOMFIX 已落地的 cave（0x00550048..0x00550080）
+ 分配器区（0x00101C00..0x00102700）」。

用法（在仓库根执行）：
  python spinfix_cave.py --iso <base.iso> --min 0x30 --top 25 --json out/cave_<tag>.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
_oc_path = os.path.join(ROOT, 'work', 'builds', 'GR_OOMFIX', 'tools', 'oomfix_cave.py')

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location('oomfix_cave', _oc_path)
oc = importlib.util.module_from_spec(spec)
sys.modules['oomfix_cave'] = oc
spec.loader.exec_module(oc)

# ── 扩展禁碰区 ────────────────────────────────────────────────────────────────
oc.FORBIDDEN = oc.FORBIDDEN + [
    (0x00550048, 0x00550080, '★GR_OOMFIX 已落地 cave（本工程绝不能再占用）'),
    (0x0054FF00, 0x00550048, 'OOMFIX cave 前置（同函数尾 + 填充，保守）'),
    (0x00550080, 0x00550200, 'OOMFIX cave 之后的 VU0 微码区（保守避让）'),
    (0x00101C00, 0x00102700, '分配器镜像（free/malloc/桶插入，F1/F2/F4 站点所在）'),
    (0x00403900, 0x00403A00, '解压器 memcpy 尾循环 0x4039C8 所在函数'),
    (0x00539110, 0x00539310, '解压器本体 0x539110（另一条线的站点）'),
]

if __name__ == '__main__':
    oc.main()
