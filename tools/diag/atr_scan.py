# -*- coding: utf-8 -*-
r"""atr_scan.py — 盘点 GR.IMG 全部 ATR 的 ActorName (会话工具)
用法: python atr_scan.py <iso> [pattern]
输出: 文件名 / EN 名 / 名长 / ClassName + 汇总 (唯一名数)。
"""
import fnmatch
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress  # noqa: E402

LBA = 19175
RE_NAME = re.compile(rb'<ActorName>(.*?)</ActorName>', re.S)
RE_CLASS = re.compile(rb'<ClassName>(.*?)</ClassName>', re.S)


def main():
    iso = sys.argv[1]
    pat = sys.argv[2] if len(sys.argv) > 2 else '*'
    data = open(iso, 'rb').read()
    base = LBA * 2048
    names_off = struct.unpack_from('<I', data, base + 0x10)[0]
    tab_end = struct.unpack_from('<I', data, base + 4)[0]
    names = [x.decode('latin-1') for x in data[base + names_off:base + tab_end].split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        if not nm.upper().endswith('.ATR'):
            continue
        r = struct.unpack_from('<12I', data, base + 0x830 + 48 * i)
        stored, real, off = r[6], r[7], r[8]
        raw = data[base + off:base + off + stored]
        if stored != real:
            outb, p = bytearray(), 0
            while p + 8 <= len(raw):
                plen, osz = struct.unpack_from('<II', raw, p)
                if plen == 0 or p + 8 + plen > len(raw):
                    break
                dec, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + plen], out_size=osz)
                outb += dec
                p += 8 + plen
            raw = bytes(outb)
        m = RE_NAME.search(raw)
        c = RE_CLASS.search(raw)
        name = m.group(1).decode('latin-1') if m else '?'
        cls = c.group(1).decode('latin-1') if c else '?'
        if fnmatch.fnmatch(name.upper(), pat.upper()) or fnmatch.fnmatch(nm.upper(), pat.upper()):
            out.append((nm, name, len(m.group(1)) if m else 0, cls, len(raw)))
    uniq = {}
    for nm, name, ln, cls, fl in out:
        uniq.setdefault(name, []).append(nm)
        print('%-26s %-24r len=%-3d cls=%-12s file=%dB' % (nm, name, ln, cls, fl))
    print('# ATR %d 个, 唯一 ActorName %d 个' % (len(out), len(uniq)), file=sys.stderr)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
