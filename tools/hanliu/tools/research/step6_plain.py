# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys, re
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
import gr_lz

data, ents = gr_lz.load_entries(os.path.join(REPO_ROOT, 'work', 'tmp', 'GR.img'))
plain = [e for e in ents if e['stored'] == e['real']]

def istext(b, mn=0.85):
    if not b: return False
    ok = sum(1 for c in b if 9 <= c <= 13 or 0x20 <= c <= 0x7E or c >= 0x80)
    return ok / len(b) >= mn

# 按扩展名统计明文条目
from collections import Counter, defaultdict
byext = defaultdict(list)
for e in plain:
    ex = e['name'].rsplit('.',1)[-1].upper() if '.' in e['name'] else '(none)'
    byext[ex].append(e)

print('=== stored==real 明文条目: 按扩展名 (数量/总字节) ===')
rows = []
for ex, es in byext.items():
    rows.append((sum(x['stored'] for x in es), len(es), ex))
for tot, n, ex in sorted(rows, reverse=True):
    print('  %-8s %4d 条 %10d B' % (ex, n, tot))

# 探测含文本的扩展: 抽样看头部
print('\n=== 文本类扩展抽样 ===')
def head(e, n=160):
    b = data[e['off']:e['off']+min(n,e['stored'])]
    return b.decode('latin-1','replace').replace('\r','').replace('\n','\n')[:160]

interesting = ['XML','TXT','TOE','ITM','IDC','SDF','CONFIG','BAT','LOG','LST','KEYS','BUT','ASS','RPF','DIR','TM','KIL','GTF','THC','ENV','SAV','SCN','CSF','PSF','ICO','AUD']
for ex in interesting:
    es = byext.get(ex, [])
    if not es: continue
    txts = [e for e in es if istext(data[e['off']:e['off']+min(512,e['stored'])])]
    print('\n[%s] %d 条 (可读文本 %d)' % (ex, len(es), len(txts)))
    for e in txts[:3]:
        print('   %-28s %8d B | %s' % (e['name'], e['stored'], head(e)))
    if len(txts) > 3:
        e = txts[3]
        print('   %-28s %8d B | %s' % (e['name'], e['stored'], head(e)))

# 全库扫描: 明文且含中文可能感兴趣的 XML 标签
print('\n=== XML 标签普查 (明文 XML 家族) ===')
tagc = Counter()
xmls = byext.get('XML',[]) + byext.get('TOE',[]) + byext.get('ITM',[]) + byext.get('IDC',[])
for e in xmls:
    b = data[e['off']:e['off']+e['stored']]
    if not istext(b[:512]): continue
    for m in re.findall(rb'<([A-Za-z_][A-Za-z0-9_]*)', b):
        tagc[m.decode()] += 1
for t, c in tagc.most_common(40):
    print('   %-24s %d' % (t, c))
