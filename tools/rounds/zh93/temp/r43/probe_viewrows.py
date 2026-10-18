import csv, io, os, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = r'work/builds/GR_ZH93/release/text'
tot = 0
for p in sorted(glob.glob(os.path.join(d, '*_view_*.csv'))):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    inj = set((r.get('injectable') or '') for r in rows)
    tot += len(rows)
    print('%-40s %7d 行  injectable=%s' % (os.path.basename(p), len(rows), sorted(inj)))
    print('      列(%d): %s' % (len(cols), ','.join(cols)))
print('view 合计 %d 行' % tot)
print()
for p in sorted(glob.glob(os.path.join(d, 'GR_ZH93_text_*.csv'))):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        n = sum(1 for _ in rd)
    print('%-40s %7d 行' % (os.path.basename(p), n))
