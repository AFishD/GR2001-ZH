# -*- coding: utf-8 -*-
r"""r57: 用**工具自己的函数**把 charset 的 `_font_compact` 元信息重写成 r57 口径 (pair_of 一个不动)。

为什么需要: r57 那次 compact 跑在文案更新**之前** ⇒ JSON 里的 note 还是 r56 文案。
这里用真实 r57 报告的数字重跑 commit_charset + stamp_charset (= make_build 收尾做的同一件事),
码位映射取自"对 GR_ZH107 再 plan 一次"(已紧凑 ⇒ 恒等映射), 因此 pair_of 逐条不变。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CS = tcslib.CHARSET
ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')

before = json.load(io.open(CS, encoding='utf-8'))
summ = json.load(io.open(os.path.join(HERE, 'compact_report.json'),
                        encoding='utf-8'))['summary']
res = FC.plan_compact(ISO107, CS, verbose=False)
n = FC.commit_charset(CS, res, summ, verbose=True)
sha107 = tcslib.sha256_file(ISO107)
FC.stamp_charset('GR_ZH107', sha107)
after = json.load(io.open(CS, encoding='utf-8'))
print('pair_of 未变: %s' % (before['pair_of'] == after['pair_of']))
for k in sorted(set(before) | set(after)):
    if k in ('pair_of', '_font_compact'):
        continue
    if before.get(k) != after.get(k):
        print('  [!!] 字段 %r 变了' % k)
print('note: %s' % after['_font_compact']['note'])
print('meta: tool_version=%s iso_version=%s iso_sha256=%s reencode=%s'
      % (after['_font_compact']['tool_version'], after['_font_compact'].get('iso_version'),
         (after['_font_compact'].get('iso_sha256') or '')[:16],
         after['_font_compact'].get('reencode')))
