# -*- coding: utf-8 -*-
"""Try parsing PC official Chinese Data/Shell/STRINGS.RES (keyed format, GBK)."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct
d = open(os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon', 'Data', 'Shell', 'STRINGS.RES'),'rb').read()
n = struct.unpack_from('<I', d, 0)[0]
print('first u32 =', n)
# try format: count? then {u32 klen}{key}{00}{u32 vlen}{val}{u16 0}
off = 4
entries = []
ok = True
for idx in range(n):
    if off + 4 > len(d): ok=False; break
    klen = struct.unpack_from('<I', d, off)[0]; off += 4
    key = d[off:off+klen]; off += klen
    if off < len(d) and d[off] == 0: off += 1  # optional NUL
    vlen = struct.unpack_from('<I', d, off)[0]; off += 4
    val = d[off:off+vlen]; off += vlen
    # expect u16 0
    tail = struct.unpack_from('<H', d, off)[0]; off += 2
    entries.append((key, val, tail))
    if tail != 0 and idx < 3:
        print('WARN tail nonzero at', idx, hex(tail))
print('parsed', len(entries), 'consumed', off, 'of', len(d), 'ok' if off==len(d) else 'MISMATCH')
for k, v, t in entries[:6]:
    print(repr(k), '->', repr(v[:60].decode('gbk', 'replace')), 'tail', t)
