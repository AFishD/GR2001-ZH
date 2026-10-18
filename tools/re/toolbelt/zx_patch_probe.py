# -*- coding: utf-8 -*-
r"""zx_patch_probe.py — 单变量探针补丁入口 (make_build 的 `--patch`)

用法（由探针名决定做什么）:
  python zx_patch_probe.py <src> <dst> --h1024      # 记录 h=1024（容器仍 640 行 / px_size 0x501F0）
  python zx_patch_probe.py <src> <dst> --growonly   # 只长大 COMMON.PAK + 平移 MENU

环境变量 ZX_PROBE 也可指定同样的名字（方便 make_build 直接用）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zx_patch_font                                                 # noqa: E402

MODES = {
    '--h1024': ['--h-declared', '0x400'],
    '--growonly': ['--grow-only'],
}


def main():
    argv = sys.argv[1:]
    extra = []
    rest = []
    for a in argv:
        if a in MODES:
            extra += MODES[a]
        else:
            rest.append(a)
    name = os.environ.get('ZX_PROBE', '')
    if name in MODES and not extra:
        extra += MODES[name]
    if not extra:
        sys.exit('需要探针名: %s (或 ZX_PROBE=<名字>)' % list(MODES))
    rep = os.path.join(zx_patch_font.R82,
                       'patch_probe%s_report.json' % extra[0].replace('--', '_'))
    return zx_patch_font.main(extra + ['--report', rep] + rest)


if __name__ == '__main__':
    sys.exit(main())
