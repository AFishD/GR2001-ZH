import json,os,glob
rows=[]
for p in glob.glob('**/build_info.json',recursive=True):
    try:
        d=json.load(open(p,encoding='utf-8-sig'))
    except Exception as e:
        rows.append((p,'PARSE_ERR '+str(e)[:60],'','')); continue
    rows.append((p, d.get('version') or d.get('tag') or '?', str(d.get('base')), str(d.get('patch'))))
rows.sort()
for p,v,b,pa in rows:
    print('%-12s | %-46s | %s   <<%s' % (v,b,pa,p))
