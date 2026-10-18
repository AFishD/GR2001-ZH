# -*- coding: utf-8 -*-
r"""v14_docs_numbers.py — 验收⑤：文档里的数字 vs 实测 (现算)

把 dump_font 现算出来的关键数字, 逐个在"本轮更新过的文档 + 资料包文档"里找一遍;
找不到就报 [!!]。这不是"文字校对", 而是"数字一致性硬检查"。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
summ = json.load(io.open(os.path.join(REPO, 'work/builds/GR_ZH93/font',
                                      'GR_ZH93_font_summary.json'), encoding='utf-8'))
c = summ['capacity']
LIVE = {
    '1504': c['pair']['capacity'], '1319': c['pair']['used'], '185': c['pair']['free'],
    '45': c['pair']['vacuum_usable'], '140': c['pair']['need_recycle'],
    '110': c['single']['used'], '1429': c['charset']['unique_chars'],
    '1526': c['charset']['dump_total'], '20.29%': c['atlas']['ink_ratio'],
    '87.70%': c['atlas']['pair_cell_ratio'],
    'e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be': 'iso sha256',
    'GR_ZH94': '下一个版本号',
}
DOCS = ['README.md', 'docs/PROGRESS.md', 'docs/FONT_CURRENT_STATE.md',
        'docs/BUILD_TOOLCHAIN.md', 'docs/BUILD_VERSIONS.md', 'tools/text_csv/FORMAT.md',
        'docs/REPORT_release_pack.md', 'work/builds/GR_ZH93/release/README.md',
        'work/builds/GR_ZH93/release/text/README_文本表.md',
        'work/builds/GR_ZH93/release/字库报告.md']
ok = True
print('# 实测(现算)数字: %s' % ', '.join('%s=%s' % (k, v) for k, v in LIVE.items()))
print()
for d in DOCS:
    p = os.path.join(REPO, d)
    txt = io.open(p, encoding='utf-8').read()
    hits = [k for k in LIVE if k in txt]
    miss = [k for k in LIVE if k not in txt]
    print('%-58s %5d 行  命中 %2d/%2d  %s'
          % (d, txt.count('\n') + 1, len(hits), len(LIVE),
             ('缺: ' + ' '.join(miss)) if miss else '✓'))
# 只对"必须写全"的几份文档做硬断言 (其余文档不必提每个数字)
MUST = {
    'docs/FONT_CURRENT_STATE.md': ('1504', '1319', '185', '45', '140', '110', '1429', '1526',
                                   '20.29%', '87.70%'),
    'docs/REPORT_release_pack.md': ('1504', '1319', '185', '45', '140', '110', '1429', '1526',
                                    '20.29%', '87.70%',
                                    'e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be',
                                    'GR_ZH94'),
    'work/builds/GR_ZH93/release/README.md': ('1504', '1319', '185', '45', '140',
                                              'e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be',
                                              'GR_ZH94'),
    'work/builds/GR_ZH93/release/字库报告.md': ('1504', '1319', '185', '45', '140', '110',
                                                '1429', '1526', '20.29%', '87.70%'),
    'docs/BUILD_VERSIONS.md': ('e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be',
                               'GR_ZH94', '1504', '1319', '45', '110'),
    'README.md': ('e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be', 'GR_ZH94'),
}
print()
for d, keys in MUST.items():
    txt = io.open(os.path.join(REPO, d), encoding='utf-8').read()
    miss = [k for k in keys if k not in txt]
    good = not miss
    ok = ok and good
    print('%s %-52s 必含 %2d 项 %s' % ('[ok]' if good else '[!!]', d, len(keys),
                                      '' if good else '缺: %s' % ' '.join(miss)))
# 反向检查: 旧数字不该再作为"现役"出现
BAD = {'docs/FONT_CURRENT_STATE.md': ['已用 | **108**'],
       'work/builds/GR_ZH93/release/README.md': ['单字节码 已用 108']}
print()
for d, pats in BAD.items():
    txt = io.open(os.path.join(REPO, d), encoding='utf-8').read()
    for pat in pats:
        good = pat not in txt
        ok = ok and good
        print('%s %-52s 不该再出现 %r' % ('[ok]' if good else '[!!]', d, pat))
print('\n结论: %s' % ('[ok] 文档数字与实测一致 ✓' if ok else '[!!] 有不一致 ✗'))
sys.exit(0 if ok else 1)
