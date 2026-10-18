import io, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r50\GR_ZH98_truncation_report.json', encoding='utf-8'))
print(d['one_line'])
for f in d['findings']:
    if f['level'] != 'error':
        print(json.dumps({k: v for k, v in f.items() if k not in ('flags',)}, ensure_ascii=False)[:400])
        print('  flags', f['flags'])
