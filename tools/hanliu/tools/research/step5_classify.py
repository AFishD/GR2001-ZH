# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
from res_encode import parse_expanded

gr = parse_expanded(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'rb').read())
menu = parse_expanded(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_res_expanded.bin'),'rb').read())

# --- 与 han_v2 手搓版对比 ---
try:
    han = open(os.path.join(REPO_ROOT, 'docs', 'han_v2', 'GR_EN_STRINGS_RES_decoded.bin'),'rb').read()
    raw = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'rb').read()
    print('han_v2 GR_EN_STRINGS_RES_decoded.bin == GR.IMG 解压态:', han == raw, '(len %d vs %d)' % (len(han), len(raw)))
except Exception as e:
    print('han_v2 compare fail', e)

# --- 精确 diff (12 条) ---
print('\n=== GR vs MENU 12 diff details ===')
for gi,(g1,g2) in enumerate(zip(gr,menu),1):
    for si,(s1,s2) in enumerate(zip(g1.strings,g2.strings)):
        if s1 != s2:
            # find diff region
            a,b = s1[0], s2[0]
            n = min(len(a),len(b))
            k = 0
            while k < n and a[k]==b[k]: k += 1
            print('G%02d.I%03d GRlen=%d MENUlen=%d first-diff@%d' % (gi,si,len(a),len(b),k))
            print('  GR  ...%r' % a[max(0,k-30):k+90].decode('latin-1','replace'))
            print('  MENU...%r' % b[max(0,k-30):k+90].decode('latin-1','replace'))

# --- 分类 ---
def S(gi, si):
    return gr[gi-1].strings[si][0].decode('latin-1','replace')

cat = {}   # (gi,si) -> (cat, note)
def tag(gi, s_range, c, note=''):
    for si in s_range:
        cat[(gi,si)] = (c, note)

# (a) 教程: G12-G18 I000-I028 教程句, I029-I034 任务头
for g in range(12,19):
    tag(g, range(0,29), 'A', '教程句(7 份相同)')
    tag(g, range(29,35), 'A2', '训练任务头')

# (c) 任务: G01-G11 MP 模式, G19-G33 / G40-G52 战役, G34-39/G53-57 MP 地图信息
for g in range(1,12):  tag(g, range(len(gr[g-1].strings)), 'C', 'MP模式规则/胜负')
for g in list(range(19,34))+list(range(40,53)):
    n = len(gr[g-1].strings)
    for si in range(n):
        t = S(g,si)
        if t.startswith('{p}') or '{p}' in t or len(t) > 200:
            cat[(g,si)] = ('C','任务简报')
        elif len(t)>3 and (t[0].isdigit() and t[1:3]==' -' or t.startswith('X - ')):
            cat[(g,si)] = ('C','任务目标')
        elif any(t.startswith(p) for p in ('Mission','Not enough','You ','The ','A ','All ','Civilian','Enemy has','US soldier','Demo Charge','Weapons Officer','No Enemy','You Have','The remaining','Ashenafi')):
            cat[(g,si)] = ('C','任务结果提示')
        else:
            cat[(g,si)] = ('C','触发点/地名')
for g in list(range(34,40))+list(range(53,58)):
    tag(g, range(len(gr[g-1].strings)), 'C', 'MP地图信息')

# (b) HUD/武器/兵种 (G58/G59 指定索引)
B58 = list(range(203,207)) + list(range(244,269)) + [456,457,458,459] + [469,470,471] + \
      list(range(531,535)) + list(range(562,573)) + [560,561,573,574] + [643,644,645,646] + \
      [670,671,732,733] + list(range(750,759))
for si in B58: cat[(58,si)] = ('B','HUD/兵种/ROE/武器提示')
for si in (5,7,8,9,10,11,13): cat[(59,si)] = ('B','HUD/射击模式')

# (e) 其他
tag(62, range(len(gr[61].strings)), 'E', '制作名单')
for g in (63,64,66): tag(g, range(len(gr[g-1].strings)), 'E', '资源文件名')
cat[(60,0)] = ('E','内部ID')

# (d) 其余全部 → 菜单/界面
from collections import Counter
cnt = Counter(); cnt2 = Counter()
for gi,g in enumerate(gr,1):
    for si in range(len(g.strings)):
        c,note = cat.get((gi,si), ('D','菜单/界面/记忆卡/MP大厅'))
        cnt[c] += 1; cnt2[(c,note)] += 1
print('\n=== 分类统计 ===')
name = {'A':'(a)教程句','A2':'(a)训练任务头','B':'(b)武器/HUD/兵种/ROE','C':'(c)任务目标/简报/无线电','D':'(d)菜单/界面','E':'(e)其他'}
for k in ('A','A2','B','C','D','E'):
    print('%-28s %4d' % (name[k], cnt[k]))
print('total', sum(cnt.values()))
print('\n细分:')
for (c,note),v in sorted(cnt2.items()):
    print('  %-3s %-24s %4d' % (c,note,v))
