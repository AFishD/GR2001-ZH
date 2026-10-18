# -*- coding: utf-8 -*-
r"""r58 调试2: 用与 plan_reencode **完全一样**的 res['cs_new']/cmap_stale 复现 DE 容器的处理 (只读)。"""
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
res = FC.plan_compact(ISO, tcslib.CHARSET, verbose=False)
res['charset_path'] = tcslib.CHARSET
mig = res['migration']
print('迁移命中: %s' % bool(mig))
stale_cs = tcslib.Charset(FC.resolve_repo_path(mig['stale_charset']))
cmap_stale = FC.CodeMap(stale_cs, res['cs_new'])
cmap_fwd = res['cmap']
print('cmap_stale.changed_pairs=%d  cmap_fwd.changed_pairs=%d'
      % (len(cmap_stale.changed_pairs), len(cmap_fwd.changed_pairs)))

iso = tcslib.Iso(ISO)
for (tag, idx) in (('MENU.IMG', 26), ('MENU.IMG', 27), ('MENU.IMG', 30)):
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    s = FC.Slot(iso, tag, lba, idx)
    h = hashlib.sha256(s.raw).hexdigest()
    rec = FC.migration_index(mig).get(h)
    print('\n%s#%d %s: role=%s' % (tag, idx, s.name, rec and rec['role']))
    if not rec:
        continue
    use_stale = rec['role'] == 'migrate'
    cmap_u = cmap_stale if use_stale else cmap_fwd
    new, st = cmap_u.remap_units(s.blob, 'dbg %s#%d' % (tag, idx))
    diff = [i for i in range(len(s.blob)) if new[i] != s.blob[i]]
    print('   use_stale=%s → 改动字节 %d %s' % (use_stale, len(diff), diff[:8]))
    print('   changed_units=%d  spans=%s' % (st['changed_units'], st['spans'][:4]))
    print('   detail.kind 判定: try_parse_lang=%s' % (FC.try_parse_lang(s.blob) is not None))
iso.close()
