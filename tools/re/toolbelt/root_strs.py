# -*- coding: utf-8 -*-
r"""root_strs.py -- 在 gsrunner.exe 里找含 GR: 的字符串及相关限制常量（READ-ONLY）"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = open(r'third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe', 'rb').read()
for pat in (b'GR: ', b'grmaxframes', b'grinput', b'watched LBA', b'burst dump start', b'dumped RAM'):
    idx = [m.start() for m in re.finditer(re.escape(pat), d)]
    print('%-22s -> %d hits %s' % (pat.decode(), len(idx), [hex(i) for i in idx[:4]]))
print()
seen = set()
i = d.find(b'GR: ')
while i >= 0:
    seg = d[max(0, i - 120):i + 120]
    for s in re.findall(rb'[ -~]{5,}', seg):
        t = s.decode('latin-1')
        if t not in seen:
            seen.add(t)
            print('  %s' % t[:150])
    i = d.find(b'GR: ', i + 1)
