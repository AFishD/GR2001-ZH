import io, json, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(r'work/builds/GR_ZH93/release/MANIFEST.json', encoding='utf-8'))
tot = sum(f['bytes'] for f in d['files'])
print('MANIFEST: %d 个文件 / %d 字节 (%.2f MB)' % (len(d['files']), tot, tot/1048576))
for f in d['files']:
    print('  %-60s %9d  %s' % (f['path'], f['bytes'], f['sha256'][:16]))
