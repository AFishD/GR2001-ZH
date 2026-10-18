# -*- coding: utf-8 -*-
r"""zx_patch_full.py — 成品盘 GR_ZH121 的 `--patch` 入口 (make_build 只传 src/dst)

    python zx_patch_full.py <src.iso> <dst.iso>
      ⇔ zx_patch_font.py <src> <dst> --apply-charset --prep-text
         --report work/builds/GR_ZH98/temp/r82/patch_gr121_report.json

顺序（都很重要）:
  ① 写字库补丁 (图集 1024x640 / 10 段容器 / COMMON.PAK 长大 66,016 / MENU.IMG 平移 +
     ISO9660 目录记录 / FONT.RES 搬带重压 / ELF 4 处 gate / 368 个字形)
  ② 同步 charset JSON（368 条新码位 + 键/练/用 迁出单字节码）
  ③ 把丰富版文本表准备成注入用（text_zh 清空 ⇒ 全盘重编码; {{BTN:E0B1}} → △）
     ⇒ 之后 make_build 的 `--inject-csv <build>/text_in` 才能解析到
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zx_patch_font                                                 # noqa: E402

if __name__ == '__main__':
    sys.exit(zx_patch_font.main([
        '--apply-charset', '--prep-text',
        '--report', os.path.join(zx_patch_font.R82, 'patch_gr121_report.json'),
    ] + sys.argv[1:]))
