# -*- coding: utf-8 -*-
r"""cross_check_r68.py — 独立复核 (不依赖注入器自述):

  A) GR_ZH114 新 dump 的标题表 text_zh  == 我这张编辑表的 text_edited (145/145)
  B) GR_ZH114 的 3 张正文表 text_zh 列 == GR_ZH111 的同一列 (2261/2261) —— 正文一个字没动
  C) GR_ZH114 / GR_ZH111 的 font dump 图集 PNG 像素 sha + FT.RES sha 相同 —— 字库没动
  D) 九份副本: 新盘 9 份的标题值 == 旧盘 9 份 (逐字节) —— 只在注入目标那一份上改
"""
import csv
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib as T                                               # noqa: E402
import dump_containers as DC                                     # noqa: E402
import font_usage as FU                                          # noqa: E402
from inject_text_csv import parse_xml_attrs                      # noqa: E402

OUT = os.path.join(HERE, 'cross_check_r68.txt')
L = []


def lo(p):
    with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def say(s):
    L.append(s)
    print(s)


def main():
    # A) ──
    mine = dict((r['id'], r['text_edited']) for r in
                lo(os.path.join(HERE, 'GR_ZH114_text_sf_titles.csv')))
    disc = dict((r['id'], r['text_zh']) for r in
                lo(os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text',
                                'GR_ZH114_text_sf_titles.csv')))
    bad = [(k, mine[k], disc.get(k)) for k in mine if disc.get(k) != mine[k]]
    say(u'A) 新盘标题表 == 我的 text_edited : %d/%d 命中%s'
        % (len(mine) - len(bad), len(mine), u'' if not bad else u'  不符 %s' % bad[:5]))

    # B) ──
    for fn111, fn114 in (('GR_ZH111_text_long.csv', 'GR_ZH114_text_long.csv'),
                         ('GR_ZH111_text_long_nowrap.csv', 'GR_ZH114_text_long_nowrap.csv'),
                         ('GR_ZH111_text_short.csv', 'GR_ZH114_text_short.csv')):
        a = lo(os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'text', fn111))
        b = lo(os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text', fn114))
        assert len(a) == len(b), (len(a), len(b))
        n_bad = sum(1 for x, y in zip(a, b)
                    if x['id'] != y['id'] or x['text_zh'] != y['text_zh'])
        say(u'B) %-30s text_zh 逐行一致: %d/%d%s'
            % (fn114, len(a) - n_bad, len(a), u'' if not n_bad else u'  ✗ %d 行不同' % n_bad))

    # C) ──
    for nm in ('GR_ZH111_font_summary.json', 'GR_ZH114_font_summary.json'):
        p = os.path.join(REPO, 'work', 'builds', nm.split('_font')[0], 'font', nm)
        d = json.load(io.open(p, encoding='utf-8'))
        say(u'C) %-30s atlas pixel sha=%s  ft_res sha=%s  记录=%s 字符=%s 缺字形=%s'
            % (nm, d['atlas']['pixel_sha256'][:16], d.get('ft_res_sha256', '-')[:16],
               d.get('ft_records'), d.get('chars'), d.get('missing_glyph')))

    # D) ──
    iso_s, iso_d = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso')), \
        T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'GR_ZH114.iso'))
    cs = T.Charset()
    cs_s = DC.sfxml_copies_of(FU.build_container_list(iso_s))
    cs_d = DC.sfxml_copies_of(FU.build_container_list(iso_d))
    n_ok = 0
    for (a, b) in zip(cs_s, cs_d):
        if a['role'] == 'zh-main':
            continue
        va = parse_xml_attrs(FU.container_blob(iso_s, a['c'])[0])
        vb = parse_xml_attrs(FU.container_blob(iso_d, b['c'])[0])
        if [x[3] for x in va] == [x[3] for x in vb]:
            n_ok += 1
        else:
            say(u'D) ✗ %s 有属性被改动' % a['name'])
    say(u'D) 9 份语言副本的 145 个 name 属性逐字节不变: %d/9%s'
        % (n_ok, u' ✓' if n_ok == 9 else u' ✗'))
    # 注入目标那一份应当有 36 处不同
    va = parse_xml_attrs(FU.container_blob(iso_s, cs_s[5]['c'])[0]) \
        if cs_s[5]['role'] == 'zh-main' else None
    tgt_s = [c for c in cs_s if c['role'] == 'zh-main'][0]
    tgt_d = [c for c in cs_d if c['role'] == 'zh-main'][0]
    va = parse_xml_attrs(FU.container_blob(iso_s, tgt_s['c'])[0])
    vb = parse_xml_attrs(FU.container_blob(iso_d, tgt_d['c'])[0])
    nd = sum(1 for x, y in zip(va, vb) if x[3] != y[3])
    say(u'D) 注入目标 MENU.IMG#283: %d/145 个属性变化 (期望 36)' % nd)
    iso_s.close()
    iso_d.close()

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
