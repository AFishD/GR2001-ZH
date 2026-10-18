# -*- coding: utf-8 -*-
r"""zero_hash4.py — 用 MENU.IMG 与 GR.IMG 里同名条目的 (slot, name) 对，暴力搜哈希函数
"""
import os
import struct
import sys
import zlib

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
SS = 2048


def load(lba):
    base = lba * SS
    hdr = struct.unpack_from('<12I', iso.mm, base)
    cnt = (hdr[3] - 0x830) // 48
    names = [x.decode('latin-1') for x in bytes(iso.mm[base + hdr[4]:base + hdr[1]]).split(b'\x00') if x]
    tab = struct.unpack_from('<4096I', iso.mm, base + hdr[8])
    return cnt, names, tab


cm, nm, tm = load(776286)
cg, ng, tg = load(19175)
def tab2map(tab, names):
    d = {}
    for i in range(4096):
        v = tab[i]
        if v != 0xFFFFFFFF and v < len(names):
            d[i] = names[v]
    return d


pm = tab2map(tm, nm)
pg = tab2map(tg, ng)
print('names 长度 MENU %d / cnt %d ; GR %d / cnt %d' % (len(nm), cm, len(ng), cg))
both = [s for s in pm if s in pg]
same = [s for s in both if pm[s] == pg[s]]
print('MENU 非空槽 %d ; GR 非空槽 %d ; 公共槽 %d ; **同名槽 %d**' % (len(pm), len(pg), len(both), len(same)))
print('  同名槽样例: %s' % [(s, pm[s]) for s in same[:20]])

PAIRS = [(s, pm[s]) for s in same] + [(s, pg[s]) for s in same]
print('  参与判定 (slot,name) 对 %d' % len(PAIRS))


def mkhash(M, init):
    def h(s, _M=M, _i=init):
        v = _i
        for c in s.encode('latin-1'):
            v = (v * _M + c) & 0xFFFFFFFF
        return v
    return h


CANDS = {}
for M in (31, 33, 37, 39, 41, 101, 131, 257, 65599, 16777619):
    for init in (0, 5381, 2166136261):
        CANDS['mul%d_i%d' % (M, init)] = mkhash(M, init)
CANDS['sdbm'] = lambda s: _sdbm(s)
CANDS['fnv1a'] = lambda s: _fnv1a(s)
CANDS['crc32'] = lambda s: zlib.crc32(s.encode('latin-1')) & 0xFFFFFFFF
CANDS['adler'] = lambda s: zlib.adler32(s.encode('latin-1')) & 0xFFFFFFFF
CANDS['sum'] = lambda s: sum(s.encode('latin-1'))
CANDS['xor'] = lambda s: _xor(s)


def _sdbm(s):
    v = 0
    for c in s.encode('latin-1'):
        v = (c + (v << 6) + (v << 16) - v) & 0xFFFFFFFF
    return v


def _fnv1a(s):
    v = 2166136261
    for c in s.encode('latin-1'):
        v ^= c
        v = (v * 16777619) & 0xFFFFFFFF
    return v


def _xor(s):
    v = 0
    for c in s.encode('latin-1'):
        v ^= c
    return v


best = []
for hn, hf in CANDS.items():
    for trans in ('raw', 'lower', 'upper'):
        for red in ('mask', 'mod4093', 'mod4096', 'shr16mask', 'shr20mask'):
            hit = 0
            for slot, name in PAIRS:
                s = {'raw': name, 'lower': name.lower(), 'upper': name.upper()}[trans]
                v = hf(s)
                if red == 'mask':
                    q = v & 0xFFF
                elif red == 'mod4093':
                    q = v % 4093
                elif red == 'mod4096':
                    q = v % 4096
                elif red == 'shr16mask':
                    q = (v >> 16) & 0xFFF
                else:
                    q = (v >> 20) & 0xFFF
                if q == slot:
                    hit += 1
            best.append((hit, hn, trans, red))
best.sort(reverse=True)
print()
print('top20 候选 (命中/总数 %d):' % len(PAIRS))
for hit, hn, trans, red in best[:20]:
    print('  %5d  %-22s %-6s %s' % (hit, hn, trans, red))

# 也试试"只依赖长度/首字符"的弱哈希
from collections import Counter
c = Counter((len(pm[s]), pm[s][0]) for s in same)
print()
print('同名槽 (len, first char) 分布 top10: %s' % c.most_common(10))
iso.close()
