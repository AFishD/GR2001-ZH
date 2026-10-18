import io, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'tools/text_csv/icon_table.py'
raw = io.open(p, 'rb').read()
lines = raw.split(b'\n')
for i in (135,136,137,138,139,143,144):
    if i-1 < len(lines):
        L = lines[i-1]
        print(i, repr(L[:120]))
line = lines[136].decode('utf-8')
print('--- decoded 137 ---')
print(repr(line))
print('normalized NFC == itself?', unicodedata.normalize('NFC', line) == line)
print('escaping:', line.encode('unicode_escape').decode())
