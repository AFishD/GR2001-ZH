# -*- coding: utf-8 -*-
r"""r58: 用"不同字占比"给普查结果做个体量化的判读 (只读 census_r58.json)。"""
import io
import json
import os
import statistics
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import font_compact as FC                                              # noqa: E402

d = json.load(io.open(os.path.join(HERE, 'census_r58.json'), encoding='utf-8'))


def variety(r):
    t = r['gen']['G2']['cjk_text']
    return (len(set(t)) / len(t)) if t else 0.0


un = [r for r in d['rows'] if not FC.registry_match(r['name'])]
reg = [r for r in d['rows'] if FC.registry_match(r['name'])]
print('登记容器 4 个的"不同字占比"(前 80 个汉字): %s'
      % ', '.join('%s %.2f' % (r['name'], variety(r)) for r in reg))
sel = [r for r in un if len(r['gen']['G2']['cjk_text']) >= 16 and variety(r) >= 0.5]
print('未登记 %d 个里, "前 80 个汉字里不同字占比 >= 0.5 且 >=16 字" 的: %d 个'
      % (len(un), len(sel)))
for r in sel[:20]:
    print('   %-38s 占比 %.2f  %r' % (r['container'], variety(r), r['gen']['G2']['cjk_text'][:48]))
print('未登记整体"不同字占比"中位数 %.3f; 登记容器 %.3f'
      % (statistics.median([variety(r) for r in un]),
         statistics.median([variety(r) for r in reg])))
