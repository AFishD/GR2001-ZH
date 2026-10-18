# -*- coding: utf-8 -*-
r"""spinfix_ramcheck.py —— 冷启动跑到某帧时，补丁字是否**逐字还在 EE RAM 里**。

用法:
  python spinfix_ramcheck.py --ram <win_fXXXXXXXX_eeram.bin> --meta <flavor.meta.json>
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--ram', required=True)
    ap.add_argument('--meta', required=True)
    a = ap.parse_args()
    ram = open(os.path.join(C.ROOT, a.ram), 'rb').read()
    meta = json.load(open(os.path.join(C.ROOT, a.meta), encoding='utf-8'))
    print('RAM  %s (%d B)' % (a.ram, len(ram)))
    print('meta %s (flavor %s, out %s)' % (a.meta, meta['flavor'], meta['out']))
    allok = True
    for s in meta['sites']:
        va, want = int(s['va'], 16), int(s['new_word'], 16)
        got, = struct.unpack_from('<I', ram, va)
        ok = (got == want)
        allok = allok and ok
        print('  site %-3s 0x%08X = %08X (期望 %08X) %s' % (s['name'], va, got, want, 'OK' if ok else 'FAIL'))
    for c in meta['caves']:
        va = int(c['va'], 16)
        bad = []
        for i, w in enumerate(c['words']):
            got, = struct.unpack_from('<I', ram, va + 4 * i)
            if got != int(w, 16):
                bad.append((va + 4 * i, got, int(w, 16)))
        allok = allok and not bad
        print('  cave %-3s 0x%08X %2d 字：%s' % (c['name'], va, len(c['words']),
                                                '全部相符 OK' if not bad else '不符 %s' % bad[:4]))
    print('⇒ 补丁在运行到该帧时%s' % ('仍在（OK）' if allok else '已被改写（FAIL）'))
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
