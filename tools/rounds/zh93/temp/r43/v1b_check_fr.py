import csv, io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for k in ('long','long_nowrap','short'):
    p = 'work/builds/GR_ZH93/text/GR_ZH93_text_%s.csv' % k
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['id'] in ('LANG:G059.I028','LANG:G059.I031'):
                print('[%s] %s' % (k, r['id']))
                print('   text_zh     = %r' % r['text_zh'])
                print('   text_en     = %r' % r['text_en'])
                print('   text_edited = %r' % r['text_edited'])
                print('   note        = %s' % r['note'][:200])
