import csv, io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
p = os.path.join(REPO, 'work/builds/GR_ZH98/text/GR_ZH98_text_long.csv')
with io.open(p, encoding='utf-8-sig', newline='') as f:
    rd = csv.reader(f)
    hdr = next(rd)
    for i, row in enumerate(rd, start=2):
        if any('\u00b1' in c for c in row):
            print('line', i, 'ncols', len(row))
            for h, c in zip(hdr, row):
                print('  %-22s | %s' % (h, c[:400].replace('\n', '\\n')))
            print('---')
