# -*- coding: utf-8 -*-
r"""r57 离线自测: 只跑新的细扫 (不写盘), 验证候选集 / 计数 / 耗时 (只读)。"""
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
CS_OLD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
CS_NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_after_r56.json')

old = tcslib.Charset(CS_OLD)
new = tcslib.Charset(CS_NEW)
iso = tcslib.Iso(ISO)
changed = set()
for p, ch in old.pair_of.items():
    if new.pair_of.get(p) != ch:
        changed.add(p)
for p, ch in new.pair_of.items():
    if old.pair_of.get(p) != ch:
        changed.add(p)
print('changed_pairs = %d' % len(changed))

containers = FC.enumerate_containers(iso)
regions = sorted((e['iso_off'], e['iso_off'] + e['stored'],
                  '%s#%d %s' % (t, i, e['name'])) for (t, _l, i, e) in containers)
knowns = FC.known_text_regions(iso, verbose=True)
t0 = time.time()
res = FC.scan_short_text(iso, old, regions, knowns, changed, verbose=True)
print('细扫耗时 %.1fs' % (time.time() - t0))
st = res['stats']
print('\n统计: %s' % json.dumps({k: v for k, v in st.items() if k != 'skipped_sample'},
                                ensure_ascii=False, indent=1))
print('\n候选串 (%d 条):' % len(res['candidates']))
cmap = FC.CodeMap(old, new)
for c in sorted(res['candidates'], key=lambda c: c['lo']):
    seg = bytes(iso.mm[c['lo']:c['hi']])
    nb, s2 = cmap.remap_units(seg, 'test')
    print('  @0x%-8X %-4d..%-4d %-18r 对偶码比 %.2f 段 %s 已知=%s'
          % (c['lo'], c['lo'], c['hi'], c['text'], c['pair_ratio'], c['runs'], c['known']))
    print('      旧 %s' % seg.hex(' '))
    print('      新 %s   (改 %d 字 / %d 字节; 旧解 %r / 新解 %r)'
          % (nb.hex(' '), s2['changed_units'], s2['changed_bytes'],
             old.decode(seg)[0], new.decode(nb)[0]))
print('\npair_ratio==1.00 的被跳过段 (Lead 点名的"巧合"家族):')
for s in st['skipped_sample']:
    if s['pair_ratio'] >= 1.0:
        seg = bytes(iso.mm[s['off']:s['off'] + s['nbytes']])
        print('  @0x%-8X %-8r raw=%-20s 理由=%-16s 串=%r'
              % (s['off'], s['text'], seg.hex(' '), s['reason'], s['cstr_text'][:40]))
iso.close()
