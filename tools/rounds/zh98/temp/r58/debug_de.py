# -*- coding: utf-8 -*-
r"""r58 调试: 为什么 MENU.IMG#26 DE_STRINGS.RES 在工具里没被"追平"? (只读)"""
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
mig = FC.STALE_MIGRATIONS[0]
idx = FC.migration_index(mig)
print('清单 %d 条' % len(idx))
iso = tcslib.Iso(ISO)
cs_old = tcslib.Charset(tcslib.CHARSET)
stale = tcslib.Charset(FC.resolve_repo_path(mig['stale_charset']))
cmap_stale = FC.CodeMap(stale, cs_old)
hits = {}
for (tag, lba, i2, e) in FC.enumerate_containers(iso):
    raw = iso.read(e['iso_off'], e['stored'])
    h = hashlib.sha256(raw).hexdigest()
    r = idx.get(h)
    if r:
        hits.setdefault(r['where'], []).append('%s#%d' % (tag, i2))
for k, v in sorted(hits.items()):
    print('  命中 %-46s %s' % (k, v))
print('命中的 where 种类 %d (清单 6 条)' % len(hits))

for (tag, lba, i2, nm) in (('MENU.IMG', FC.MENU_LBA, 26, 'DE'), ('MENU.IMG', FC.MENU_LBA, 27, 'ES'),
                           ('MENU.IMG', FC.MENU_LBA, 30, 'EN.TXT')):
    s = FC.Slot(iso, tag, lba, i2)
    r = idx.get(hashlib.sha256(s.raw).hexdigest())
    print('\n%s#%d %s: 清单命中=%s role=%s' % (tag, i2, nm, bool(r), r and r['role']))
    if not r:
        continue
    new, st = cmap_stale.remap_units(s.blob, 'dbg %s#%d' % (tag, i2))
    diff = sum(1 for k in range(len(s.blob)) if new[k] != s.blob[k])
    print('   cmap_stale(G0→现役) 改 %d 字节 (changed_units=%d)  %s'
          % (diff, st['changed_units'], st.get('spans', [])[:5]))
    new2, st2 = FC.CodeMap(cs_old, cs_old).remap_units(s.blob, 'dbg2')
    print('   cmap(cs_old→cs_old) 改 %d 字节 (对照)' % sum(1 for k in range(len(s.blob))
                                                          if new2[k] != s.blob[k]))
iso.close()
