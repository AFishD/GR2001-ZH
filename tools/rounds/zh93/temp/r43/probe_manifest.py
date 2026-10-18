import io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(r'work/builds/GR_ZH93/release/MANIFEST.json', encoding='utf-8'))
print('generated', d['generated'])
print('iso_sha256', d['iso_sha256'])
tot = 0
for f in d['files']:
    tot += f['bytes']
    print('%-58s %10d  %s  %s' % (f['path'], f['bytes'], f['sha256'][:12], f['note']))
print('files', len(d['files']), 'total bytes', tot, '(%.1f MB)' % (tot/1048576))
