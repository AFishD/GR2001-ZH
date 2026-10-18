# -*- coding: utf-8 -*-
import re
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
data = b'BOOT2 = cdrom0:\\SLUS_206.13;1\x00\x01\x02<MissionFile>hello world this is text'
for pat in (rb'[\x20-\x7e]{12,}', rb'[\x20-\x7E]{12,}', rb'[\x20-\x7e]+'):
    rx = re.compile(pat)
    print('%r → %r' % (pat, [m.group(0) for m in rx.finditer(data)]))
rx = re.compile(b'[' + re.escape(bytes(range(0x20, 0x7f))) + b']{12,}')
print('escaped → %r' % [m.group(0) for m in rx.finditer(data)])
