# -*- coding: utf-8 -*-
r"""hk_disc_tables.py — 从 5 张盘的 meta.json 生成「逐站点回退清单」markdown."""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

DISKS = [('HK_01_all_text_off', 'G1+G2+G3+G4'),
         ('HK_02_g1_off', 'G1'),
         ('HK_03_g2_off', 'G2'),
         ('HK_04_g3_off', 'G3'),
         ('HK_05_g4_off', 'G4')]


def main():
    out = []
    out.append('# 5 张 HK 打靶盘的逐站点回退清单')
    out.append('')
    out.append('每张盘的完整**逐字节**清单（VA / ISO / 原字节 hex / 新字节 hex）'
               '见同目录 `HK_xx*.meta.json` 的 `patch_list`（按站点）与 `byte_diff_runs`（按连续区段）。')
    out.append('')
    for (d, tag) in DISKS:
        m = json.load(io.open(os.path.join(H.OUT, d + '.meta.json'), encoding='utf-8'))
        pl = m['patch_list']
        out.append('## %s — 组 %s' % (d, tag))
        out.append('')
        out.append('* 站点 **%d** ；回退字节 **%d** ；与基底实测差异 **%d** B'
                   % (m['n_sites'], m['reverted_bytes'], m['byte_diff_total']))
        out.append('* sha256 `%s` ；尺寸 %d' % (m['sha256'], m['size']))
        out.append('* 差异连续区段 %d 个' % len(m['byte_diff_runs']))
        out.append('')
        out.append('| # | VA | ISO 偏移 | 长 | 符号 | 组 |')
        out.append('|---|---|---|---|---|---|')
        for i, s in enumerate(pl):
            out.append('| %d | 0x%X | 0x%X | %d | `%s` | %s |'
                       % (i, s['va'], s['iso_off'], s['length'],
                          s['symbol'].split('__')[0], s['group']))
        out.append('')
    txt = '\n'.join(out)
    with io.open(os.path.join(H.EVID, 'hk_disc_tables.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print('wrote hk_disc_tables.md (%d lines)' % txt.count('\n'))


if __name__ == '__main__':
    main()
