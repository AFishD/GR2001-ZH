import csv, io, re, sys, glob, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
RE = re.compile(r'\{\{BTN:([0-9A-Fa-f]{4})\}\}')
per = collections.Counter(); cols = collections.Counter()
tot = 0
for p in sorted(glob.glob(r'work/builds/GR_ZH93/text/GR_ZH93_text_*.csv')):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            for c in ('text_zh','text_en','text_edited','note'):
                for m in RE.finditer(r.get(c) or ''):
                    per[m.group(1).upper()] += 1; cols[c] += 1; tot += 1
print('标记总处数 =', tot)
print('按标记  =', dict(per))
print('按列    =', dict(cols))
