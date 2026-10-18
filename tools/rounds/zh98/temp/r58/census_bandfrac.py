# -*- coding: utf-8 -*-
r"""r58: 判据 —— 未登记容器里的"汉字"有多少来自**单字节码带** (与码位重排无关)?

`charset.codes` 把 0x80..0xFF 里的一部分字节映射成汉字 (单字节码带, ~110 个)。
这一带**从不因紧凑重排而变** (工具只改 pair_of) ⇒ 落在带内的"汉字"是像素/压缩数据里的噪声,
换码根本改不动它。真文本 (语言表/帮助文件) 的汉字绝大多数在带外 (对偶码)。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import font_compact as FC                                              # noqa: E402
import tcslib                                                          # noqa: E402

cs = tcslib.Charset(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'))
band = set(cs.codes.values())                    # 单字节码带里的字符
print('单字节码带字符数 %d (例: %s)' % (len(band), ''.join(sorted(band)[:16])))
d = json.load(io.open(os.path.join(HERE, 'census_r58.json'), encoding='utf-8'))


def out_frac(r):
    t = r['gen']['G2']['cjk_text']
    if not t:
        return None
    return sum(1 for c in t if c not in band) / len(t)


un = [r for r in d['rows'] if not FC.registry_match(r['name'])]
reg = [r for r in d['rows'] if FC.registry_match(r['name'])]
print('\n登记容器 (前 80 汉字的"带外占比"):')
for r in reg:
    print('   %-30s %.2f' % (r['name'], out_frac(r) or 0))
hi = [r for r in un if (out_frac(r) or 0) >= 0.5]
print('\n未登记 %d 个里, "带外占比 >= 0.5" 的: %d 个' % (len(un), len(hi)))
for r in sorted(hi, key=lambda r: -(out_frac(r) or 0))[:20]:
    print('   %-38s 带外 %.2f  %r' % (r['container'], out_frac(r), r['gen']['G2']['cjk_text'][:44]))
