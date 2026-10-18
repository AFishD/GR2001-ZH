# -*- coding: utf-8 -*-
r"""pending_dump_r71.py — 把「20 条待确认」在本轮里的处置逐条落成清单。

输出 pending_r71.txt:
  A) 本轮已改的 11 条 (A 类 9 + B 类 2)          —— 改动前/后
  B) 明确不动的 7 条 (任务书点名)                —— 原文原封不动列出
  C) 评估后决定不动的 2 条 (A0084 / A0113)       —— 含阻断证据
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
V114 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114')
SRC = os.path.join(V114, 'text', 'GR_ZH114_text_sf_titles.csv')
NEW = os.path.join(HERE, 'GR_ZH117_text_sf_titles.csv')
FONT = os.path.join(V114, 'font', 'GR_ZH114_font_charset.csv')
OUT = os.path.join(HERE, 'pending_r71.txt')

FROZEN = [
    ('SFXML:A0055', u'定向地雷 (M18) -> 反步兵地雷 (M18)', u'要不要给全称 (用户 T0010 原话「M18 定向反步兵地雷」)'),
    ('SFXML:A0066', u'SA-80 -> 卡宾枪', u'军迷认知是突击步枪, 两说'),
    ('SFXML:A0077', u'Bizon -> 野牛冲锋枪 (9mm)', u'丢拉丁型号的代价'),
    ('SFXML:A0078', u'9A-91 -> 紧凑型', u'变长 +2 字 / +34px'),
    ('SFXML:A0143', u'开发访谈 1 -> 开发手记 1', u'EN 原版菜单名也是 Interview, 两可'),
    ('SFXML:A0144', u'开发访谈 2 -> 开发手记 2', u'同上'),
    ('SFXML:A0145', u'开发访谈 3 -> 开发手记 3', u'同上'),
]
KEEP2 = [
    ('SFXML:A0084', u'测距望远镜 (AN/GVS-5) -> 激光测距仪 (AN/GVS-5)',
     u'两者等长 (16 字/Δpx=0), 但**换了名词**: EN 原名抓的是 Binoculars 那一半, '
     u'建议抓的是 Range Finder 那一半; round68 体检自己写「现译其实更贴合用途」。'
     u'两个口径都站得住 ⇒ 归入"有争议", 本轮不动。'),
    ('SFXML:A0113', u'极限危机 -> 恐惧的总和',
     u'**做不了 + 有争议**: `恐` `惧` 两个字**根本不在 charset JSON 里** (实测 not_in_charset); '
     u'备选台译 `惊天核网` 的 `核` 在 JSON 里但 has_glyph=0 (盘上没画)。'
     u'⇒ 现役字库下两种写法都写不进去, 只能等字库扩容; 本轮不动。'),
]


def main():
    def read(p):
        with io.open(p, encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    a, b = read(SRC), read(NEW)
    fa = dict((r['id'], r) for r in a)
    fb = dict((r['id'], r) for r in b)
    L = [u'# 20 条待确认 —— round71 处置清单',
         u'# 表: %s (盘上现值) vs %s (本轮注入表)' % (os.path.relpath(SRC, REPO),
                                                     os.path.relpath(NEW, REPO)),
         u'']
    L.append(u'== A) 本轮已改 11 条 (A 类 9 + B 类 2) ==')
    L.append(u'%-14s %-6s %-34s %-12s %-14s' % (u'id', u'tag', u'英文原名', u'盘上现值', u'本轮新值'))
    ch = [r for r in b if r['text_edited'] != r['text_zh']]
    for r in ch:
        L.append(u'%-14s %-6s %-34s %-12s %-14s'
                 % (r['id'], r['tag'], r['text_en'] or u'(空)', r['text_zh'] or u'(空)',
                    r['text_edited']))
    L.append(u'  共 %d 条' % len(ch))
    L.append(u'')
    L.append(u'== B) 任务书点名"不要动"的 7 条 —— 原封不动 (盘上现值 == 本轮注入值) ==')
    L.append(u'%-14s %-6s %-34s %-16s %-8s %s'
             % (u'id', u'tag', u'英文原名', u'现译(未动)', u'状态', u'待你定的点'))
    for (rid, what, why) in FROZEN:
        r = fb[rid]
        same = (r['text_zh'] == r['text_edited'] == fa[rid]['text_edited'])
        L.append(u'%-14s %-6s %-34s %-16s %-8s %s'
                 % (rid, r['tag'], r['text_en'] or u'(空)', r['text_edited'],
                    u'未动 ✓' if same else u'!! 变了', why))
        L.append(u'%-14s  建议写法: %s' % (u'', what))
    L.append(u'')
    L.append(u'== C) 评估后决定不动的 2 条 (同样"现值 == 注入值") ==')
    for (rid, what, why) in KEEP2:
        r = fb[rid]
        same = (r['text_zh'] == r['text_edited'] == fa[rid]['text_edited'])
        L.append(u'%-14s %-6s EN=%-34s 现译=%-18s %s'
                 % (rid, r['tag'], r['text_en'], r['text_edited'],
                    u'未动 ✓' if same else u'!! 变了'))
        L.append(u'   建议写法: %s' % what)
        L.append(u'   依据: %s' % why)
    L.append(u'')
    # 字库自证
    font = {}
    with io.open(FONT, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            font[row['char']] = row['has_glyph']
    L.append(u'== D) 字库实测 (GR_ZH114 charset dump) ==')
    for s in (u'音乐', u'荒漠围攻士兵', u'荒漠围攻车辆', u'恐惧的总和', u'惊天核网'):
        miss = [c for c in s if c not in font]
        nog = [c for c in s if c in font and font[c] != '1']
        L.append(u'   %-8s 不在 charset=%-6s 有码位无字形=%-6s'
                 % (s, u''.join(miss) or u'-', u''.join(nog) or u'-'))
    L.append(u'   (对照: `恐`/`惧` 连码位都没有 ⇒ A0113 两种写法都写不进去; '
             u'`核` 只有码位没字形)')
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(u'\n'.join(L) + u'\n')
    print(u'\n'.join(L))
    print(u'\nwrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
