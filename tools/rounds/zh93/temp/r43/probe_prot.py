import json, io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(r'tools/font_pipeline/data/charset_compiled_zh16.json', encoding='utf-8'))
codes = {int(v): k for k, v in d['codes'].items()}
prot = [int(x,16) for x in d['protected']]
mk = [int(x,16) for x in d['mark_codes']]
print('protected =', ['%02X'%b for b in prot])
print('mark_codes=', ['%02X'%b for b in mk])
for b in prot:
    print('  %02X -> in codes? %s (%s)' % (b, b in codes, codes.get(b,'')))
print('conflict now:', [(codes[b], '%02X'%b) for b in prot if b in codes], [(codes[b],'%02X'%b) for b in mk if b in codes])
