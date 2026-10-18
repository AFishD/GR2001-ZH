# -*- coding: utf-8 -*-
r"""lead_stale_count.py — 量化: 现役盘 GR_ZH100 的 SFXML name= 属性里有多少是"过期字节"

判据: 同一段字节, 用"写入时的 charset"(重排前 charset_before_repack.json) 解出的文本,
      与用"当前 charset"解出的文本**不同** => 该属性过期(实机显示的是后者, 而作者想写的是前者)。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import repack_leak_scan as R                            # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH100', 'GR_ZH100.iso')
CUR = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                     'charset_compiled_zh16.json'), encoding='utf-8'))
OLD = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                                     'charset_before_repack.json'), encoding='utf-8'))

blob = R.load_blob(R.tcslib.Iso(ISO), 'SFXML')['blob']
print('SFXML blob %d 字节' % len(blob))

attrs = R.sfxml_attributes(blob, R.tcslib.Charset(os.path.join(
    REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')))
print('属性条数: %d ; 首条结构: %s' % (len(attrs), json.dumps(attrs[0], ensure_ascii=False)[:220]))


def maps(cs):
    pm = {}
    for ch, (b1, b2) in cs['pair_of'].items():
        pm[(b1, b2)] = ch
    return pm, dict(cs['codes'])


pm_cur, sm_cur = maps(CUR)
pm_old, sm_old = maps(OLD)

stale, same = [], 0
for a in attrs:
    raw = a.get('bytes_hex') or a.get('raw') or a.get('bytes') or a.get('hex')
    if isinstance(raw, str):
        raw = bytes.fromhex(raw.replace(' ', ''))
    if not raw:
        continue
    t_cur = R.decode_with(pm_cur, sm_cur, raw)
    t_old = R.decode_with(pm_old, sm_old, raw)
    if t_cur != t_old:
        stale.append((raw.hex(' '), t_old, t_cur))
    else:
        same += 1

print()
print('=' * 70)
print('现役盘 GR_ZH100 的 SFXML name= 属性过期情况')
print('=' * 70)
print('  未过期 (两种 charset 解出相同): %d' % same)
print('  **过期 (实机显示与作者本意不同): %d**' % len(stale))
for hx, t_old, t_cur in stale[:20]:
    print('    %-46s  作者本意 %-16s  实机显示 %s' % (hx, t_old, t_cur))
if len(stale) > 20:
    print('    … 共 %d 条' % len(stale))
