# -*- coding: utf-8 -*-
"""看一眼 IMG 之外那 645 段"换码后意义变了"的巧合到底在哪儿 (只读)。"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
import font_compact as FC                                            # noqa: E402

old = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56',
                                  'charset_before_r56.json'))
new = tcslib.Charset()
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH106', 'GR_ZH106.iso'))
for off in (4166, 4998, 7704, 10434, 17901, 32768 + 4):
    seg = iso.read(off - 16, 96)
    print('off=%d (LBA %d)  bytes: %s' % (off, off // 2048, seg[:48].hex(' ')))
    print('    旧解得: %r' % old.decode(iso.read(off, 24))[0])
    print('    新解得: %r' % new.decode(iso.read(off, 24))[0])
# 这些偏移落在什么区?
print('\nLBA 0..15 = ISO 系统区; LBA 16..17 = PVD; ELF 在 LBA 295')
hits = FC.scan_raw_iso(iso, old, verbose=False)
import font_compact
regions = sorted((e['iso_off'], e['iso_off'] + e['stored'], 'x')
                 for (_t, _l, _i, e) in FC.enumerate_containers(iso))
outside = [h for h in hits if FC.who(regions, h['off']) == '(IMG 之外 / 未归属)']
print('IMG 之外命中 %d 段; 偏移范围 %d..%d' % (len(outside), min(h['off'] for h in outside),
                                              max(h['off'] for h in outside)))
buck = {}
for h in outside:
    lb = h['off'] // 2048
    buck[lb] = buck.get(lb, 0) + 1
print('按 LBA 分布 (前 20):', sorted(buck.items())[:20])
iso.close()
