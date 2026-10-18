# -*- coding: utf-8 -*-
r"""probe_ram.py -- read-only probe of the 6 new F10 dumps.

Checks: patch presence (F4 station/cave), mstate/top/bucket snapshot,
0x102180 / 0x81FF0 code bytes, and dump/regs metadata.

Usage: python probe_ram.py [--json out.json]
"""
import os
import sys
import json
import struct
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
DUMPS = os.path.join(ROOT, 'work', 'builds', 'GR_HOOKEMU_QT2', 'qt', 'hookdumps')
NAMES = ['hook_10470_hotkey_f10', 'hook_13112_hotkey_f10', 'hook_14025_hotkey_f10',
         'hook_16893_hotkey_f10', 'hook_19095_hotkey_f10', 'hook_19671_hotkey_f10']


def u32(ram, va):
    return struct.unpack_from('<I', ram, va & 0x1FFFFFFF)[0]


def u64(ram, va):
    return struct.unpack_from('<Q', ram, va & 0x1FFFFFFF)[0]


def meta(path):
    d = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                d[k] = v
    return d


def main():
    out = {}
    for name in NAMES:
        d = os.path.join(DUMPS, name)
        ram_path = os.path.join(d, 'ee_ram.bin')
        with open(ram_path, 'rb') as f:
            ram = f.read()
        m = meta(os.path.join(d, 'meta.txt'))
        rec = {
            'frame': m.get('frame'),
            'pc': m.get('pc'),
            'epc': m.get('epc'),
            'reason': m.get('reason'),
            'ring_total': m.get('ring_entries_total'),
            'ram_sha256': hashlib.sha256(ram).hexdigest(),
            'words': {},
        }
        probes = {
            'F4_station_0x102588': 0x00102588,
            'F4_cave_0x41A35C': 0x0041A35C,
            'F4_cave_j_back_0x41A370': 0x0041A370,
            'F4_cave_j_bail_0x41A378': 0x0041A378,
            'malloc_entry_0x102050': 0x00102050,
            'loop_0x1024D0': 0x001024D0,
            'loop_0x102584': 0x00102584,
            'ownbin_0x10216C': 0x0010216C,
            'ownbin_0x102180': 0x00102180,
            'ownbin_0x1021A0': 0x001021A0,
            'ownbin_0x1021D0': 0x001021D0,
            'lowcode_0x81FC0': 0x00081FC0,
            'lowcode_0x81FF0': 0x00081FF0,
            'OOMFIX_station_0x539174': 0x00539174,
            'OOMFIX_cave_0x550048': 0x00550048,
            'bin126_fd_0x55BB98': 0x0055BB98,
            'bin126_bk_0x55BB9C': 0x0055BB9C,
            'mstate_0x55B7A0': 0x0055B7A0,
            'topfield_0x55B7A8': 0x0055B7A8,
            'const_0x55B7AC': 0x0055B7AC,
        }
        for k, va in probes.items():
            rec['words'][k] = '%08X' % u32(ram, va)
        # qwords of interest
        rec['qwords'] = {
            'mstate_q0_0x55B7A0': '%016X' % u64(ram, 0x0055B7A0),
            'bin126_q_0x55BB98': '%016X' % u64(ram, 0x0055BB98),
            'top_head_0x55B7B0': '%016X' % u64(ram, 0x0055B7B0),
        }
        top = u32(ram, 0x0055B7A8)
        rec['top'] = '%08X' % top
        if 0x100000 <= top < 0x2000000:
            head = u64(ram, top + 8)
            size = head & 0x1FFFFFFE
            rec['top_head'] = '%016X' % head
            rec['top_size'] = '%X' % size
            rec['heap_end'] = '%08X' % ((top + size) & 0xFFFFFFFF)
        out[name] = rec
        print('== %s frame=%s pc=%s epc=%s' % (name, rec['frame'], rec['pc'], rec['epc']))
        print('   F4 station=%s cave0=%s caveJ=%s caveBail=%s' % (
            rec['words']['F4_station_0x102588'], rec['words']['F4_cave_0x41A35C'],
            rec['words']['F4_cave_j_back_0x41A370'], rec['words']['F4_cave_j_bail_0x41A378']))
        print('   top=%s head=%s size=%s heap_end=%s' % (
            rec['top'], rec.get('top_head'), rec.get('top_size'), rec.get('heap_end')))
        print('   bin126=%s (fd=%s bk=%s) 0x55B7ACconst=%s' % (
            rec['qwords']['bin126_q_0x55BB98'], rec['words']['bin126_fd_0x55BB98'],
            rec['words']['bin126_bk_0x55BB9C'], rec['words']['const_0x55B7AC']))
        print('   0x102180=%s 0x1021A0=%s 0x1021D0=%s 0x81FF0=%s 0x81FC0=%s' % (
            rec['words']['ownbin_0x102180'], rec['words']['ownbin_0x1021A0'],
            rec['words']['ownbin_0x1021D0'], rec['words']['lowcode_0x81FF0'],
            rec['words']['lowcode_0x81FC0']))
    if '--json' in sys.argv:
        p = sys.argv[sys.argv.index('--json') + 1]
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print('wrote', p)


if __name__ == '__main__':
    main()
