# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/slus_scan/dwarf_probe.py (逐字复制)。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""Probe DWARF structure inside the single .debug section of SLUS_206.13."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
d = open(ELF, 'rb').read()
DBG_OFF, DBG_SIZE = 0x6B43A0, 0x199A0C8
dbg = d[DBG_OFF:DBG_OFF+DBG_SIZE]
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'slus_scan', 'debug_sec.bin'), 'wb').write(dbg)

# Try CU header at 0
p = 0
ulen = struct.unpack_from('<I', dbg, p)[0]
ver = struct.unpack_from('<H', dbg, p+4)[0]
aboff = struct.unpack_from('<I', dbg, p+6)[0]
addr = dbg[p+10]
print("first CU: len=0x%X ver=%d abbrev_off=0x%X addr_size=%d" % (ulen, ver, aboff, addr))
# show first bytes of abbrev table region
print("bytes @0x0:", ' '.join('%02x' % c for c in dbg[:32]))
print("bytes @abbrev 0x%X:" % aboff, ' '.join('%02x' % c for c in dbg[aboff:aboff+32]))

# Walk CUs, print name + offset, stop after listing; build index
cus = []
p = 0
n = 0
while p < DBG_SIZE and n < 100000:
    if p + 11 > DBG_SIZE: break
    ulen = struct.unpack_from('<I', dbg, p)[0]
    if ulen == 0 or ulen > DBG_SIZE: break
    ver = struct.unpack_from('<H', dbg, p+4)[0]
    aboff = struct.unpack_from('<I', dbg, p+6)[0]
    start = p
    p += 4 + ulen
    cus.append((start, ulen, ver, aboff))
    n += 1
print("total CUs:", len(cus))
print("last CU start=0x%X" % cus[-1][0])
