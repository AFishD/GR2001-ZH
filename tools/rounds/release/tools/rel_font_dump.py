# -*- coding: utf-8 -*-
r"""rel_font_dump.py -- 用**工程既有**的 rb_verify_k2.py 驱动 dump_font 家族核对,
但把它的 OUTDIR 改到本轮的写入根 (work\builds\GR_RELEASE\temp), 不动别人的目录。

    python work\builds\GR_RELEASE\tools\rel_font_dump.py --iso <final.iso> [--allpat ...] [--charset ...]

★ 重要: 本驱动设 `RB_NO_BASE=1` —— 原判据的参照盘 `GR_ZH124.iso` / 来源盘 `GR_F364.iso`
  已不在磁盘上, rb_verify_k2.py 的 [addr] 两行会**退化为空真**(vacuous pass)。
  因此本驱动在调用前把这两行的语义显式标注为"未达成", 真正的"逐 texel == 基底"由
  rel_atlas_base.py 用**同几何的直接基底** GR_REBUILD2400.iso 做 (更强)。
"""
import argparse
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
RB = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'tools', 'rb_verify_k2.py')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_RELEASE', 'temp')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--allpat', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                    'GR_REBUILD2400_allpat.iso'))
    ap.add_argument('--base', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                   'GR_REBUILD2400.iso'))
    ap.add_argument('--charset', default=os.path.join(
        REPO, 'work', 'builds', 'GR_HASHR', 'backup',
        'charset_compiled_zh16.json.before_hashr'))
    ap.add_argument('--tag', default='rel_final')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    outm = os.path.join(OUT, 'rbverify')
    os.makedirs(outm, exist_ok=True)

    os.environ['RB_NO_BASE'] = '1'
    spec = importlib.util.spec_from_file_location('rbv', RB)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['rbv'] = mod
    spec.loader.exec_module(mod)
    mod.OUTDIR = outm                      # ★ 只改输出根, 判据代码一字不动
    print('=' * 100)
    print('[rel_font_dump] rb_verify_k2.py 的输出根已改为 %s' % outm)
    print('[rel_font_dump] RB_NO_BASE=1 ⇒ 该工具的 [addr] 现役槽/r83 两行**不是判据**'
          '(参照盘 GR_ZH124/GR_F364 已不在盘上, 那两行会退化成 1736/1736 与 136/136 的空真);')
    print('[rel_font_dump]   真正的「逐 texel == 基底」见 rel_atlas_base.py [C] (2350/2350, 同几何基底)')
    print('=' * 100)
    rc = mod.main(['--iso', os.path.abspath(a.iso), '--allpat', os.path.abspath(a.allpat),
                   '--base', os.path.abspath(a.base), '--tag', a.tag,
                   '--charset', os.path.abspath(a.charset)])
    log = '\n'.join(mod.LOG)
    with io.open(os.path.join(OUT, 'rel_font_dump.txt'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write(log + '\n')
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
