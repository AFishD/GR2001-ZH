# -*- coding: utf-8 -*-
r"""heap_audit.py -- read-only heap audit of the 6 new F10 dumps (and optional old dumps).

Structure (per docs/REPORT_HEAP_EXHAUSTION.md, re-verified in this round):
  mstate (a0)          = 0x0055B7A0
  top chunk pointer    @ 0x0055B7A8   (also bin[0].fd slot)
  const 0x0055B798     @ 0x0055B7AC
  bin i pseudo-chunk   = 0x0055B798 + 8*i ; fd @ +8*i+0x10?  -> fd @ 0x0055B7A8+8i, bk @ +4
  chunk: prev_size @ +0 (64b), head @ +8 (64b, size = head & 0x1FFFFFFE), fd @ +16, bk @ +20
  empty bin i: fd == bk == (0x0055B798 + 8*i)

Usage: python heap_audit.py [--json out.json] [--dumproot PATH]
"""
import os
import sys
import json
import struct
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
DUMPS = os.path.join(ROOT, 'work', 'builds', 'GR_HOOKEMU_QT2', 'qt', 'hookdumps')
NEW = ['hook_10470_hotkey_f10', 'hook_13112_hotkey_f10', 'hook_14025_hotkey_f10',
       'hook_16893_hotkey_f10', 'hook_19095_hotkey_f10', 'hook_19671_hotkey_f10']
OLD = ['hook_19701_hotkey_f10', 'hook_23444_hotkey_f10']

MSTATE = 0x0055B7A0
BINS_BASE = 0x0055B798          # pseudo-chunk of bin 0
TOP_FIELD = 0x0055B7A8
NBINS = 128
HEAP_BASE = 0x0065AEA0
RAM_SIZE = 32 * 1024 * 1024
SIZE_MASK = 0x1FFFFFFE          # lui 0x1FFF / ori 0xFFFE


def u32(ram, va):
    return struct.unpack_from('<I', ram, va & 0x1FFFFFFF)[0]


def u64(ram, va):
    return struct.unpack_from('<Q', ram, va & 0x1FFFFFFF)[0]


def audit(name, ram, verbose=True):
    rec = {'dump': name, 'ram_sha256': hashlib.sha256(ram).hexdigest()}
    top = u32(ram, TOP_FIELD)
    rec['top'] = '%08X' % top
    top_head = u64(ram, top + 8)
    top_size = top_head & SIZE_MASK
    rec['top_head'] = '%016X' % top_head
    rec['top_size'] = '%X' % top_size
    heap_end = (top + top_size) & 0xFFFFFFFF
    rec['heap_end'] = '%08X' % heap_end
    rec['heap_total'] = top_size
    rec['heap_base'] = '%08X' % HEAP_BASE

    # ---- walk the chunk chain from base to top ----
    p = HEAP_BASE
    chunks = []
    seen = set()
    bad = []
    while p < top and len(chunks) < 200000:
        if p in seen:
            bad.append({'addr': '%08X' % p, 'why': 'loop_in_walk'})
            break
        seen.add(p)
        head = u64(ram, p + 8)
        size = head & SIZE_MASK
        prev_inuse = head & 1
        if size == 0 or (size & 7) or p + size > RAM_SIZE:
            bad.append({'addr': '%08X' % p, 'head': '%016X' % head, 'size': '%X' % size,
                        'why': 'bad_size'})
            break
        chunks.append({'addr': p, 'size': size, 'free': (prev_inuse == 0)})
        p = (p + size) & 0xFFFFFFFF
    rec['walk_chunks'] = len(chunks)
    rec['walk_reached_top'] = (p == top)
    rec['walk_bad'] = bad[:8]
    used = sum(c['size'] for c in chunks)
    free_chunks = [c for c in chunks if c['free']]
    free_bytes = sum(c['size'] for c in free_chunks)
    rec['account'] = {
        'base': '%08X' % HEAP_BASE,
        'top': rec['top'],
        'heap_bytes_base_to_top': (top - HEAP_BASE),
        'heap_head_total': top_size,
        'walked_used_bytes': used,
        'walked_free_bytes': free_bytes,
        'walked_free_blocks': len(free_chunks),
        'walked_chunks': len(chunks),
        'heap_used_pct': round(100.0 * used / float(top - HEAP_BASE), 2) if top > HEAP_BASE else None,
    }

    # ---- bins ----
    bins = []
    empty_ok = 0
    broken = []
    for i in range(NBINS):
        slot = (BINS_BASE + 8 * i) & 0xFFFFFFFF
        fd = u32(ram, slot + 0x10)
        bk = u32(ram, slot + 0x14)
        pseudo = slot
        entry = {'bin': i, 'slot_fd': '0055%04X' % (0xB7A8 + 8 * i), 'fd': '%08X' % fd, 'bk': '%08X' % bk}
        if fd == pseudo and bk == pseudo:
            empty_ok += 1
            entry['state'] = 'empty'
        bins.append(entry)
    # walk each non-empty bin
    for e in bins:
        if e.get('state') == 'empty':
            continue
        i = e['bin']
        head = (BINS_BASE + 8 * i) & 0xFFFFFFFF
        node = int(e['fd'], 16)
        chain = []
        ok = True
        for _ in range(4096):
            if node == head:
                break
            if node in [c['addr'] for c in chain]:
                ok = False
                chain.append({'addr': '%08X' % node, 'why': 'cycle'})
                break
            if not (HEAP_BASE <= node < RAM_SIZE) or (node & 7):
                ok = False
                chain.append({'addr': '%08X' % node, 'why': 'outside_heap_or_unaligned'})
                break
            h = u64(ram, node + 8)
            sz = h & SIZE_MASK
            nfd = u32(ram, node + 0x10)
            nbk = u32(ram, node + 0x14)
            chain.append({'addr': '%08X' % node, 'size': '%X' % sz, 'fd': '%08X' % nfd,
                          'bk': '%08X' % nbk, 'next_bk': '%08X' % nbk})
            if sz == 0 or (sz & 7):
                ok = False
                chain[-1]['why'] = 'bad_size'
                break
            if nbk == node and nfd == node:
                ok = False
                chain[-1]['why'] = 'self_loop'
                break
            node = nbk
        else:
            ok = False
            chain.append({'why': 'chain_too_long'})
        e['chain'] = chain
        e['chain_ok'] = ok
        if not ok:
            broken.append(e)
    rec['bins_empty'] = empty_ok
    rec['bins_nonempty'] = NBINS - empty_ok
    rec['bins_broken'] = broken
    rec['bin126'] = {'fd': bins[126]['fd'], 'bk': bins[126]['bk'],
                     'state': bins[126].get('state', 'bad')}
    # ---- search for the bad word elsewhere in RAM ----
    pat = struct.pack('<I', int(bins[126]['fd'], 16)) if bins[126]['fd'] != '00000000' else None
    if pat:
        hits = []
        start = 0
        while True:
            k = ram.find(pat, start)
            if k < 0 or len(hits) >= 40:
                break
            hits.append('%08X' % k)
            start = k + 1
        rec['bin126_word_hits'] = {'pattern': bins[126]['fd'], 'count_capped40': len(hits), 'offsets': hits}
    if verbose:
        print('== %s  %s' % (name, rec['ram_sha256'][:16]))
        print('   top=%s size=%s heap_end=%s  walk: chunks=%d reached_top=%s bad=%s' % (
            rec['top'], rec['top_size'], rec['heap_end'], len(chunks), rec['walk_reached_top'], bad[:2]))
        print('   account: %s' % json.dumps(rec['account']))
        print('   bins: empty=%d nonempty=%d broken=%d' % (empty_ok, NBINS - empty_ok, len(broken)))
        for b in broken[:4]:
            print('     bin %d fd=%s bk=%s chain=%s' % (b['bin'], b['fd'], b['bk'],
                  json.dumps(b['chain'][:3])))
        print('   bin126: fd=%s bk=%s' % (rec['bin126']['fd'], rec['bin126']['bk']))
        if 'bin126_word_hits' in rec:
            print('   bin126 word %s appears %d times (capped): %s' % (
                rec['bin126_word_hits']['pattern'], rec['bin126_word_hits']['count_capped40'],
                rec['bin126_word_hits']['offsets'][:12]))
    return rec


def main():
    only_new = '--old' not in sys.argv
    names = NEW if only_new else NEW + OLD
    out = {}
    for n in names:
        p = os.path.join(DUMPS, n, 'ee_ram.bin')
        with open(p, 'rb') as f:
            ram = f.read()
        out[n] = audit(n, ram)
    if '--json' in sys.argv:
        jp = sys.argv[sys.argv.index('--json') + 1]
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print('wrote', jp)


if __name__ == '__main__':
    main()
