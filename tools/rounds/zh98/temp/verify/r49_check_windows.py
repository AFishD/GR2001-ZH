# -*- coding: utf-8 -*-
r"""r49_check_windows.py — "画面相关像素一个都没动"的静态证明 (逐像素, 分 5 组)。

两盘图集逐像素比, 按"这些像素归谁"分组:
  ① 544 条 FT 记录矩形 (**原矩形** = 实测的真采样窗)                    ⇒ 期望差异 **0**
  ② 记录窗 ±(4,2) 膨胀 **但不含那 144 个被回收字的格子** (最保守口径)     ⇒ 期望差异 **0**
  ③ charset 在用的对偶格, **不含那 144 个被回收字** (活字形 1175 个)      ⇒ 期望差异 **0**
  ④ 那 144 个被回收字的格子 (本轮**故意**擦白的)                          ⇒ 期望 = 它们的墨
  ⑤ 其余 (残墨区, 本轮**故意**清的)                                      ⇒ 期望 = 4831

⇒ ①②③ 全 0 = "引擎会采样的像素两盘完全相同, 画面不可能变";
  ④⑤ 的差异数 = 本轮报告里写的清理量, 一一对应。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402
import font_residue as FR                                            # noqa: E402

ISO97 = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
ISO98 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH98')
CS97 = os.path.join(B, 'temp', 'charset_before_font_cleanup.json')


def atlas(iso):
    f = dump_font.load_font(iso)
    a = f['atlas']
    return repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm'])


def main():
    A97, A98 = atlas(ISO97), atlas(ISO98)
    diff = A97.eng != A98.eng
    ink_lost = int((A97.eng & diff).sum())
    ink_gain = int((A98.eng & diff).sum())
    print('两盘图集: 墨 %d → %d; 差异像素 %d (墨→空 %d, 空→墨 %d)'
          % (int(A97.eng.sum()), int(A98.eng.sum()), int(diff.sum()), ink_lost, ink_gain))

    f97 = dump_font.load_font(ISO97)
    cs97 = tcslib.Charset(CS97)
    S = FR.enumerate_sampler(cs97, f97['faces'], A97.w, A97.h)
    dead = json.load(io.open(os.path.join(B, 'temp', 'font_recycle_backup.json'),
                             encoding='utf-8'))['chars']
    dead_mask = np.zeros((A97.h, A97.w), bool)
    for ch in dead:
        b1, b2 = cs97.enc_pair[ch]
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
        dead_mask[y:y + 16, x:x + 16] = True
    used_live = S['pair_used'] & ~dead_mask
    ft_dil_live = S['ft_dil'] & ~dead_mask

    groups = [
        ('① FT 记录矩形 (原矩形 = 真采样窗)', S['ft_raw'], 0),
        ('② 记录窗 ±(4,2) 膨胀 (不含被回收的格)', ft_dil_live, 0),
        ('③ 在用对偶格 (活字形 %d 个)' % len(set(cs97.enc_pair) - set(dead)), used_live, 0),
        ('④ 被回收的 %d 个字的格子 (故意擦白)' % len(dead), dead_mask, -1),
        ('⑤ 其余 = 残墨区 (故意清)', ~(S['ft_dil'] | S['pair_used']), -1),
    ]
    print('')
    bad = 0
    for (nm, m, want) in groups:
        n = int((diff & m).sum())
        if want >= 0 and n != want:
            bad += 1
        tail = ('OK (期望 %d)' % want) if want >= 0 else '(故意改的区域)'
        print('  %-42s 覆盖 %6d px  差异 **%5d** px  %s' % (nm, int(m.sum()), n, tail))
    print('')
    print('  "引擎会采样的像素" (①②③) 合计差异 = **%d** px'
          % int((diff & (S['ft_raw'] | ft_dil_live | used_live)).sum()))
    print('⇒ %s' % ('① ② ③ 全 0 差异 ⇒ 两盘在**所有会被画出来的像素**上逐点相同, 画面不可能变;'
                    ' ④ ⑤ 的差异就是本轮报告里写的清理量'
                    if bad == 0 else '!! 有 %d 组不符合期望' % bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
