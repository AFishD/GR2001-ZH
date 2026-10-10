# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct, re
d = open(os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon', 'Data', 'Shell', 'STRINGS.RES'),'rb').read()
# scan for {u32 klen}{ascii key} candidates
keys = []
i = 4
while i < len(d) - 4:
    klen = struct.unpack_from('<I', d, i)[0]
    if 1 <= klen <= 64 and i+4+klen <= len(d):
        kb = d[i+4:i+4+klen]
        if all(0x20 <= b <= 0x7e for b in kb):
            keys.append((i, klen, kb.decode('latin-1')))
            i += 4 + klen
            continue
    i += 1
print('candidate keys:', len(keys))
for pos, kl, k in keys[:120]:
    print(hex(pos), kl, repr(k))

# distinct key patterns
import re, collections
pat = collections.Counter(re.sub(r'\d+', 'N', k) for _,_,k in keys)
print('--- key patterns ---')
for p, n in pat.most_common():
    print(n, p)
