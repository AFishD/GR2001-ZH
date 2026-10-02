# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
import gr_lz, lz77_decode

data, ents = gr_lz.load_entries(os.path.join(REPO_ROOT, 'work', 'tmp', 'GR.img'))

def get(name):
    e = [x for x in ents if x['name'] == name][0]
    raw = data[e['off']:e['off']+e['stored']]
    out, stats = lz77_decode.decode_entry(raw)
    bad = [s for s in stats if s[3]]
    print('%-20s stored=%d real=%d substreams=%d decoded=%d errors=%d sum(osz)=%d'
          % (name, e['stored'], e['real'], len(stats), len(out), len(bad), sum(s[2] for s in stats)))
    return e, out

e, out = get('EN_STRINGS.RES')
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'wb').write(out)
assert len(out) == e['real'], 'size mismatch'
print('saved expanded %d bytes, == real OK' % len(out))

# 与 MENU 展开态对比
menu = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_res_expanded.bin'),'rb').read()
print('MENU expanded=%d  GR expanded=%d  delta=%+d' % (len(menu), len(out), len(out)-len(menu)))
if len(out) == len(menu):
    diffs = [i for i in range(len(out)) if out[i]!=menu[i]]
    print('byte diffs:', len(diffs))
else:
    # 找公共前缀/后缀
    n = min(len(out), len(menu))
    i = 0
    while i < n and out[i]==menu[i]: i += 1
    j = 0
    while j < n-i and out[len(out)-1-j]==menu[len(menu)-1-j]: j += 1
    print('common prefix=%d common suffix=%d -> MENU-only middle=%d bytes, GR-only middle=%d bytes'
          % (i, j, len(menu)-i-j, len(out)-i-j))
    open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'diff_menu_gr.bin'),'wb').write(menu[i:len(menu)-j])
    open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'diff_gr_menu.bin'),'wb').write(out[i:len(out)-j])
    print('dumped diff middle chunks')

# 顺手解压其余语言 RES 供统计
import struct
for nm in ['DE_STRINGS.RES','ES_STRINGS.RES','FR_STRINGS.RES','IT_STRINGS.RES','STRINGS.TXT','EN_STRINGS.TXT']:
    try:
        e2, o2 = get(nm)
        safe = nm.replace('.','_').lower()
        open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_%s_expanded.bin') % safe,'wb').write(o2)
    except Exception as ex:
        print(nm, 'FAIL', ex)
