# -*- coding: utf-8 -*-
r"""r62_recon_sf_copies.py — 侦察: 盘上到底有几份 *_SPECIAL_FEATURE.XML, 各有多少含中文属性。

只读 ISO, 不写任何盘面文件; 输出 JSON 供后续验收比对。
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import font_usage as FU                                               # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
OUT = os.path.join(HERE, 'r62_recon_sf_copies.json')

ITEM_RE = re.compile(rb'<(item|group|studio)\b([^>]*)>')
ANYTAG_RE = re.compile(rb'<([A-Za-z_][\w:.-]*)\b([^>]*)>')
ATTR_RE = re.compile(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
NONASCII_RE = re.compile(r'[^\x00-\x7f]')

iso = T.Iso(ISO)
cs = T.Charset()
conts = FU.build_container_list(iso)
sf = [c for c in conts if 'SPECIAL_FEATURE' in c['name'].upper()]
print('=== 盘上 *_SPECIAL_FEATURE.* 容器: %d 个 ===' % len(sf))
rep = dict(iso=os.path.relpath(ISO, REPO).replace('\\', '/'),
           copies=[], totals=dict())
for c in sf:
    blob, _raw = FU.container_blob(iso, c)
    xml = cs.decode(blob)[0]
    # ① item/group/studio 的 name= 属性
    names, by_tag, by_attr = [], collections.Counter(), collections.Counter()
    for m in ITEM_RE.finditer(blob):
        tag = m.group(1).decode('latin-1')
        for am in ATTR_RE.finditer(m.group(2)):
            key = am.group(1).decode('latin-1')
            val = am.group(2)
            txt = cs.decode(val)[0]
            by_tag[tag] += 1
            by_attr[key] += 1
            if NONASCII_RE.search(txt):
                names.append(dict(tag=tag, attr=key,
                                  off=m.start(2) + am.start(2), n=len(val), text=txt))
    # ② **任何**标签上含中文的属性
    anycjk, by_tag_any = [], collections.Counter()
    for m in ANYTAG_RE.finditer(blob):
        tag = m.group(1).decode('latin-1')
        for am in ATTR_RE.finditer(m.group(2)):
            txt = cs.decode(am.group(2))[0]
            if NONASCII_RE.search(txt):
                anycjk.append(dict(tag=tag, attr=am.group(1).decode('latin-1'),
                                   off=m.start(2) + am.start(2), n=len(am.group(2)),
                                   text=txt))
                by_tag_any[tag] += 1
    n_cjk_run = len([x for x in names if CJK_RE.search(x['text'])])
    e = dict(img=c['img'], idx=c['idx'], name=c['name'], kind=c['kind'],
             stored=c['stored'], real=c['real'], blob=len(blob),
             is_copies0=(c['lba'], c['idx']) == (T.RES['SFXML']['copies'][0][1],
                                                 T.RES['SFXML']['copies'][0][2]),
             n_items_tags=len(ITEM_RE.findall(blob)),
             attrs_by_tag=dict(by_tag), attrs_by_attr=dict(by_attr),
             n_attr_nonascii=len(names), n_attr_cjk_run=n_cjk_run,
             n_anytag_nonascii=len(anycjk), anytag_by_tag=dict(by_tag_any),
             anytag_by_attr=dict(collections.Counter(x['attr'] for x in anycjk)),
             n_text_el=len(T.TEXT_RE.findall(blob)))
    rep['copies'].append(e)
    print('# %-14s #%-4s kind=%-6s stored=%7d real=%7d blob=%7d  item/group/studio标签=%3d'
          % (c['img'], c['idx'], c['kind'], c['stored'], c['real'], len(blob),
             e['n_items_tags']))
    print('    含非 ASCII 的 item/group/studio 属性 %3d (其中含汉字 %3d)  '
          '★任何标签含非 ASCII 属性 %3d  <text> 元素 %d  copies[0]=%s'
          % (e['n_attr_nonascii'], n_cjk_run, e['n_anytag_nonascii'], e['n_text_el'],
             e['is_copies0']))
    print('    属性名分布 (item/group/studio): %s' % dict(by_attr))
    print('    含非 ASCII 的属性名分布 (任何标签): %s' % e['anytag_by_attr'])
rep['totals'] = dict(copies=len(sf),
                     n_attr_nonascii=sum(x['n_attr_nonascii'] for x in rep['copies']),
                     n_attr_cjk_run=sum(x['n_attr_cjk_run'] for x in rep['copies']),
                     n_anytag_nonascii=sum(x['n_anytag_nonascii'] for x in rep['copies']))
print('\n=== 合计 ===')
print('# 副本 %d 份; item/group/studio 含非 ASCII 属性 %d 个 (含汉字 %d); '
      '任何标签含非 ASCII 属性 %d 个'
      % (rep['totals']['copies'], rep['totals']['n_attr_nonascii'],
         rep['totals']['n_attr_cjk_run'], rep['totals']['n_anytag_nonascii']))

# ③ 与 lead 的 123 对表 (只算 copies[0] 的 item/group/studio 非 ASCII)
c0 = [x for x in rep['copies'] if x['is_copies0']]
if c0:
    print('# copies[0] (%s#%s) item/group/studio 含非 ASCII 属性 = %d'
          % (c0[0]['img'], c0[0]['idx'], c0[0]['n_attr_nonascii']))
    # 用户点名串的原文 (从 copies[0] 全属性里找)
    blob, _r = FU.container_blob(iso, [c for c in sf if c['is_copies0']][0]) \
        if False else (None, None)
json.dump(rep, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('# → %s' % os.path.relpath(OUT, REPO).replace('\\', '/'))
iso.close()
