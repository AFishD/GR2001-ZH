import csv, io, os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base = r'work/builds/GR_ZH93/text'
for k in ('long','long_nowrap','short'):
    p = os.path.join(base, 'GR_ZH93_text_%s.csv' % k)
    n=0; ed=0; marks=0; fr=[]
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            n+=1
            te=r.get('text_edited') or ''; tz=r.get('text_zh') or ''
            if te!=tz: ed+=1
            if '{{BTN:' in tz or '{{BTN:' in te:
                marks+=1
                if 'E0E7' in tz or 'E0F1' in tz or 'E0E7' in te or 'E0F1' in te:
                    fr.append((r['id'], tz, te))
    print('%-12s rows=%4d edited=%3d hasBTN=%3d' % (k, n, ed, marks))
print('--- 含 E0E7/E0F1 的行 ---')
for x in fr: print(repr(x))
