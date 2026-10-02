# -*- coding: utf-8 -*-
"""Census of han chars across all PC text; coverage vs gbtext.def / Chinese.dat; misc greps."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import os, re, struct

BASE = os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon')
ART = os.path.join(BASE, 'Data', 'Shell', 'Art')
SHELL = os.path.join(BASE, 'Data', 'Shell')

charset = open(os.path.join(ART, 'gbtext.def'), 'rb').read().decode('gbk')
cset = set(charset)
cdat = open(os.path.join(BASE, 'Chinese.dat'), 'rb').read().decode('gbk')
cdatset = set(cdat)

def han_of(s):
    return set(c for c in s if ord(c) > 0x7f)

# --- strings.txt (Data/Shell) ---
s_txt = open(os.path.join(SHELL, 'strings.txt'), 'rb').read().decode('gbk')
# --- STRINGS.RES values ---
d = open(os.path.join(SHELL, 'STRINGS.RES'), 'rb').read()
keys, values = [], []
off = 4
n = struct.unpack_from('<I', d, 0)[0]
for _ in range(n):
    klen = struct.unpack_from('<I', d, off)[0]; off += 4
    key = d[off:off+klen].decode('latin1'); off += klen + 1  # +NUL
    nsub = struct.unpack_from('<I', d, off)[0]; off += 4
    subs = []
    for _ in range(nsub):
        ln = struct.unpack_from('<I', d, off)[0]; off += 4
        subs.append(d[off:off+ln].decode('gbk')); off += ln + 2
    off += 4  # terminator u32 0
    keys.append(key); values.append(subs)
print('STRINGS.RES: %d keys, key list sample: %s' % (len(keys), keys[:8]))
print('  all keys:', keys)
allsubs = [s for subs in values for s in subs]
print('  total substrings: %d, total chars: %d' % (len(allsubs), sum(len(s) for s in allsubs)))

# --- mods strings ---
mod_txt = {}
for m in ['Mp1', 'Mp2', 'Origmiss']:
    p = os.path.join(BASE, 'Mods', m, 'Shell', 'strings.txt')
    if os.path.exists(p):
        mod_txt[m] = open(p, 'rb').read().decode('gbk', errors='replace')

# census
sets = {
    'Data/Shell/strings.txt': han_of(s_txt),
    'STRINGS.RES': han_of(''.join(allsubs)),
}
for m, t in mod_txt.items():
    sets['Mods/%s/strings.txt' % m] = han_of(t)
allhan = set()
for k, v in sets.items():
    print('%-28s non-ascii unique: %d' % (k, len(v)))
    allhan |= v
print('UNION non-ascii across text sources:', len(allhan))
print('  of which CJK ideographs:', sum(1 for c in allhan if 0x4e00 <= ord(c) <= 0x9fff))
print('  punctuation/other:', ''.join(sorted(c for c in allhan if not (0x4e00 <= ord(c) <= 0x9fff))))
missing_gb = sorted(c for c in allhan if c not in cset)
print('  NOT in gbtext.def (%d):' % len(missing_gb), ''.join(missing_gb))
missing_cd = sorted(c for c in allhan if c not in cdatset)
print('  NOT in Chinese.dat (%d):' % len(missing_cd), ''.join(missing_cd))

# full-charset stats
import collections
def gbk_quartet(c):
    b = c.encode('gbk')
    return (b[0], b[1])
leads = collections.Counter(c.encode('gbk')[0] for c in charset)
print('gbtext.def GBK lead-byte distribution:', dict(sorted(leads.items())))
# ascii check in values
asc_in_vals = set(c for s in allsubs for c in s if ord(c) < 128)
print('ASCII chars inside STRINGS.RES values:', ''.join(sorted(asc_in_vals)))
asc_in_txt = set(c for c in s_txt if ord(c) < 128 and c not in '\r\n\t" ')
print('ASCII inside strings.txt values (approx):', ''.join(sorted(asc_in_txt)))

# --- exe/igor greps ---
for exe_name in ['GhostRecon.exe', 'igor.exe']:
    exe = open(os.path.join(BASE, exe_name), 'rb').read()
    print('==== %s (%d bytes) ====' % (exe_name, len(exe)))
    for pat in [b'gbtext', b'text.def', b'Chinese', b'BIG5', b'chinese', b'.dat', b'GetACP', b'936', b'950', b'Font load succeeded', b'IDR_SXM']:
        hits = [m.start() for m in re.finditer(re.escape(pat), exe)]
        print('  ', pat, len(hits), hits[:8])
    i = exe.find(b'Chinese Font load succeeded')
    if i > 0:
        print('   success-msg ctx:', ''.join(chr(x) if 32 <= x < 127 else '.' for x in exe[i-120:i+60]))
    for m in list(re.finditer(b'(?i)big5text|gbtext', exe))[:4]:
        o = m.start()
        print('   name ctx @%d:' % o, ''.join(chr(x) if 32 <= x < 127 else '.' for x in exe[o-40:o+40]))
