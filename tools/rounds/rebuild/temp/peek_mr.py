import json
p=r'work\builds\GR_TXMIG\temp\build\migrate_report.json'
d=json.load(open(p,encoding='utf-8'))
def walk(o,pre='',depth=0):
    if depth>2: return
    if isinstance(o,dict):
        for k,v in o.items():
            if isinstance(v,(dict,list)):
                print('%s%s: %s(len=%d)'%('  '*depth,k,type(v).__name__,len(v)))
                walk(v,pre+'/'+k,depth+1)
            else:
                s=str(v)
                print('%s%s = %s'%('  '*depth,k,s[:120]))
    elif isinstance(o,list):
        print('%s[list len=%d] first=%s'%('  '*depth,len(o),str(o[0])[:300] if o else ''))
walk(d)
