# -*- coding: utf-8 -*-
r"""hashr_imm_scan.py — 全 ELF 扫「0xB1/0xB5 立即数消费者」(只读)

用法: python work/builds/GR_HASHR/tools/hashr_imm_scan.py <elf> [<elf> ...]
ELF PT_LOAD[0]: VA 0x100000 @ file 0x80  ⇒ VA = 0x100000 + (off - 0x80)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import cave_dis as CD                                                       # noqa: E402

OPS = {0x09: 'addiu', 0x0D: 'ori', 0x0C: 'andi', 0x0A: 'slti', 0x0B: 'sltiu',
       0x0E: 'xori', 0x0F: 'lui', 0x24: 'lbu', 0x20: 'lb', 0x25: 'lhu', 0x21: 'lh'}
WANT = {0x00B1, 0x00B5, 0xFFB1, 0xFFB5}
VA0, OFF0 = 0x100000, 0x80


def scan(path, limit=0x2000000):
    data = open(path, 'rb').read(min(os.path.getsize(path), limit))
    n = (len(data) - OFF0) // 4
    out = []
    for i in range(n):
        off = OFF0 + 4 * i
        w = struct.unpack_from('<I', data, off)[0]
        op = (w >> 26) & 0x3F
        if op not in OPS:
            continue
        imm = w & 0xFFFF
        if imm not in WANT:
            continue
        va = VA0 + off - OFF0
        out.append((va, off, w, CD.dis(w, va)))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print('=' * 100)
        print(p)
        rows = scan(p)
        print('  命中 %d 处 (前 4 MB)' % len(rows))
        for (va, off, w, txt) in rows:
            print('   VA 0x%08X  file 0x%07X  %08X  %s' % (va, off, w, txt))
