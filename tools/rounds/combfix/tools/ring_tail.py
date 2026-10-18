# -*- coding: utf-8 -*-
r"""ring_tail.py -- last-N watch-ring pattern per dump + largest free block in the heap walk.

Usage: python ring_tail.py [--n 1000] [--json out.json]
"""
import collections
import json
import os
import re
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
DUMPS = os.path.join(ROOT, 'work', 'builds', 'GR_HOOKEMU_QT2', 'qt', 'hookdumps')
NAMES = ['hook_10470_hotkey_f10', 'hook_13112_hotkey_f10', 'hook_14025_hotkey_f10',
         'hook_16893_hotkey_f10', 'hook_19095_hotkey_f10', 'hook_19671_hotkey_f10']
TOP_FIELD = 0x0055B7A8
SIZE_MASK = 0x1FFFFFFE
HEAP_BASE = 0x0065AEA0
REC = re.compile(r'^\s*(\d+)\s+(\d+)\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+(\d+)\s+([WR])\s+(\d+)\s+([0-9A-Fa-f]{16})')


def u32(ram, va):
    return struct.unpack_from('<I', ram, va & 0x1FFFFFFF)[0]


def u64(ram, va):
    return struct.unpack_from('<Q', ram, va & 0x1FFFFFFF)[0]


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    n = 1000
    if '--n' in sys.argv:
        n = int(sys.argv[sys.argv.index('--n') + 1])
    out = {}
    for name in NAMES:
        d = os.path.join(DUMPS, name)
        recs = []
        p = os.path.join(d, 'ring.txt')
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    m = REC.match(line)
                    if m:
                        recs.append(m.groups())
        tail = recs[-n:]
        by_pc = collections.Counter(r[2] for r in tail)
        by_addr = collections.Counter(r[3] for r in tail)
        by_frame = collections.Counter(int(r[1]) for r in tail)
        frames = sorted(by_frame)
        ram = open(os.path.join(d, 'ee_ram.bin'), 'rb').read()
        top = u32(ram, TOP_FIELD)
        # largest free block by walking the chain
        p2, biggest, biggest_at, nfree, freebytes = HEAP_BASE, 0, 0, 0, 0
        seen = set()
        while p2 < top and p2 not in seen:
            seen.add(p2)
            head = u64(ram, p2 + 8)
            size = head & SIZE_MASK
            if size == 0 or (size & 7) or p2 + size > 32 << 20:
                break
            if (head & 1) == 0:      # next chunk has PREV_INUSE clear -> this chunk is free
                nfree += 1
                freebytes += size
                if size > biggest:
                    biggest, biggest_at = size, p2
            p2 += size
        out[name] = dict(
            ring_records_total=len(recs), tail_n=len(tail),
            tail_frames=[frames[0], frames[-1]] if frames else None,
            tail_by_pc=dict(by_pc.most_common(8)),
            tail_by_addr=dict(by_addr.most_common(6)),
            tail_last3=[list(r) for r in tail[-3:]],
            largest_free_block=biggest, largest_free_at='0x%08X' % biggest_at,
            free_blocks=nfree, free_bytes=freebytes,
            top='0x%08X' % top)
        r = out[name]
        print('== %s' % name)
        print('   ring.txt 记录 %d 条；尾部 %d 条的帧区间 %s' % (r['ring_records_total'], r['tail_n'], r['tail_frames']))
        print('   尾部按 PC：%s' % json.dumps(r['tail_by_pc']))
        print('   尾部按 addr：%s' % json.dumps(r['tail_by_addr']))
        print('   最大空闲块 0x%X (%s)，空闲块 %d 个 / %d B（%.2f MB）' % (
            r['largest_free_block'], r['largest_free_at'], r['free_blocks'], r['free_bytes'],
            r['free_bytes'] / 1048576.0))
        print('   尾部最后 3 条：%s' % json.dumps(r['tail_last3']))
    if '--json' in sys.argv:
        jp = sys.argv[sys.argv.index('--json') + 1]
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print('wrote', jp)


if __name__ == '__main__':
    main()
