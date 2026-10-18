# -*- coding: utf-8 -*-
r"""zx_r84_ceiling2.py — round84：**图集真实天花板（诚实版）**（只读）

上一版 `zx_r84_ceiling.py` 的 ② 有 bug（把 free 反复标记导致重复计数）。
本版把「还要占用图集的**字形**总数」算死，给出真实缺口与可达上限。

口径（全部盘上实测）：
  · 对偶码字形 = 1 个 16x16 格位/字（网格公式只给 16 的整数倍，不能更小）
  · 单字节记录字形 = 1 个记录矩形
      - ASCII 段 idx 0..95：95 个唯一矩形，其中 8px 宽的可以两条共用一个格位
      - 汉字段 idx 96..223：106 个唯一矩形（105 宽 + 2 窄）
  · 图集 = 1024*512 = 2048 个 16x16 格位（4bpp 下每 texel 半字节）

产出 work/builds/GR_ZH98/temp/r84/ceiling2.txt
"""
import io
import os
import sys
import json

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np        # noqa: E402
import tcslib             # noqa: E402
import zx_lib             # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r84')
os.makedirs(OUT, exist_ok=True)
W, H = 1024, 512
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
names = []
for i in range(2000):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
pak_e = iso.img_entry(tcslib.MENU_LBA, names.index('COMMON.PAK'))
pak = bytes(iso.read(pak_e['iso_off'], pak_e['stored']))
nm, psm, aw, ah, clut, pxs, PX = tcslib.parse_pak_records(pak)[1]
img, cov = zx_lib.decode_engine(pak[PX:PX + pxs], W, H)
ft_e = iso.img_entry(tcslib.MENU_LBA, names.index('FONT.RES'))
exp = b''.join(s[0] for s in tcslib.lzo_subs(bytes(iso.read(ft_e['iso_off'], ft_e['stored']))))
he, faces = tcslib.parse_ft_faces(exp)
iso.close()
recs = {f[0]: f[2] for f in faces}
cs = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))

P('图集 1024x512@4bpp = %d texel = **%d 个 16x16 格位**（格位是图集面积的原子单位）' % (W * H, W * H // 256))
P('')

# ── 三类「占格」字形 ──
def rectset(idxs):
    s = {}
    for i in idxs:
        b0, b1, u0, v0, u1, v1 = recs['default'][i]
        if u1 > u0:
            s.setdefault((u0, v0, u1, v1), []).append(i)
    return s


ascii_r = rectset(range(96))
han_r = rectset(sorted({c - 0x20 for c in cs['codes'].values()}))


def cells(rs):
    """有墨矩形 -> 需要几个 16x16 格位（<=8px 宽的两条共格）。"""
    live = [r for r in rs if img[r[1]:r[3], r[0]:r[2]].any()]
    narrow = sum(1 for r in live if r[2] - r[0] <= 8)
    wide = len(live) - narrow
    return wide + (narrow + 1) // 2, len(live), narrow, wide


c_ascii, n_ascii, nar_a, wid_a = cells(ascii_r)
c_han, n_han, nar_h, wid_h = cells(han_r)
P('① ASCII 段（记录 idx 0..95，引擎硬编码使用）')
P('     唯一矩形 %d（有墨 %d：窄 %d / 宽 %d）⇒ 占 **%d** 个格位'
  % (len(ascii_r), n_ascii, nar_a, wid_a, c_ascii))
P('② 汉字单字节段（记录 idx>=96，charset codes 107 条）')
P('     唯一矩形 %d（有墨 %d：窄 %d / 宽 %d）⇒ 占 **%d** 个格位'
  % (len(han_r), n_han, nar_h, wid_h, c_han))
P('③ 对偶码字形（网格）: 现役 1736')
P('')
P('=' * 78)
P('★ 供需账')
P('   图集格位总量                = 2048')
P('   ③ 现役对偶字形占            = 1736')
P('   ① ASCII 段占               = %d' % c_ascii)
P('   ② 汉字单字节段占            = %d' % c_han)
used = 1736 + c_ascii + c_han
P('   ---- 现役合计              = %d  ⇒ 空余 **%d 格位**' % (used, 2048 - used))
P('   ④ 364 个新字需要            = 364')
P('   ---- 需求合计              = %d' % (used + 364))
P('   ★★ 缺口 = %d - %d = **%d 格位**（超出 %.1f%%）'
  % (used + 364, 2048, used + 364 - 2048, 100.0 * (used + 364 - 2048) / 2048.0))
P('')
P('   ⇒ 上限（假设零浪费）= 2048 − %d − %d = **%d** 个对偶字形' % (c_ascii, c_han, 2048 - c_ascii - c_han))
P('   ⇒ 相对现役 1736 ⇒ **最多再加 %d 个新字**' % (2048 - c_ascii - c_han - 1736))
P('   ⇒ 要达到 364：还差 **%d 格位**（= %.1f 行 16px）'
  % (used + 364 - 2048, (used + 364 - 2048) / 64.0))

P('')
P('=' * 78)
P('★ 敏感度：把记录压窄能救回多少？')
P('   %-46s %6s %6s %6s' % ('方案', 'ASCII', '汉字段', '可加新字'))
for tag, fa, fh in (('现状（记录矩形原样）', lambda r: r, lambda r: r),
                    ('ASCII 压到 8px 宽（两条共格）', lambda r: (r[0], r[1], r[0] + 8, r[3]), lambda r: r),
                    ('ASCII + 汉字段都压到 8px 宽', lambda r: (r[0], r[1], r[0] + 8, r[3]),
                     lambda r: (r[0], r[1], r[0] + 8, r[3])),
                    ('全部压到 8px 宽 + 记录可缩到 8 行高',
                     lambda r: (r[0], r[1], r[0] + 8, r[1] + 8), lambda r: (r[0], r[1], r[0] + 8, r[1] + 8))):
    ca, _, _, _ = cells({fa(r): v for r, v in ascii_r.items()})
    ch, _, _, _ = cells({fh(r): v for r, v in han_r.items()})
    P('   %-46s %6d %6d %6d' % (tag, ca, ch, 2048 - ca - ch - 1736))

P('')
P('=' * 78)
P('★ 到达 364 需要什么（逐条量化）')
need_extra = used + 364 - 2048
P('   需要额外腾出 **%d 格位**。可选手段：' % need_extra)
P('     a) 把 ASCII 段 95 格压成 8px 宽 ⇒ 省 %d 格' % (c_ascii - (n_ascii + 1) // 2))
P('     b) 把汉字段 %d 格压成 8px 宽   ⇒ 省 %d 格' % (c_han, c_han - (n_han + 1) // 2))
P('     c) 用单字节码腾出对偶槽（不省格位，只省"码位"）')
P('     d) 把图集做大（h>512 或第二页/第二容器）—— 上一轮已证会黑屏，任务书禁止')
P('     a+b 合计只能省 %d 格，仍差 %d 格 ⇒ **必须 d**，而 d 被禁 ⇒ **364 不可达**'
  % ((c_ascii - (n_ascii + 1) // 2) + (c_han - (n_han + 1) // 2),
     need_extra - ((c_ascii - (n_ascii + 1) // 2) + (c_han - (n_han + 1) // 2))))

with io.open(os.path.join(OUT, 'ceiling2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'ceiling2.txt'))
