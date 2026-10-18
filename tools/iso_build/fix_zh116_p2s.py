# -*- coding: utf-8 -*-
r"""fix_zh116_p2s.py — 读 PCSX2 即时存档 (.p2s, zip + zstd method 93)

本机 anaconda 的 zipfile 不认 method 93(zstd), 但 `zstandard` 模块在。
⇒ 手工定位 local file header 的 data 偏移, 用 `zstandard` 解压。
只读, 不写任何非本工程目录的东西。

CLI:
  python tools/iso_build/fix_zh116_p2s.py list <p2s>
  python tools/iso_build/fix_zh116_p2s.py extract <p2s> <entry> <out>
"""
import os
import struct
import sys
import zipfile

import zstandard

LFH_SIG = 0x04034b50


def _data_off(fp, info):
    fp.seek(info.header_offset)
    hdr = fp.read(30)
    if len(hdr) < 30 or struct.unpack('<I', hdr[:4])[0] != LFH_SIG:
        raise ValueError('bad local file header for %s' % info.filename)
    nlen, elen = struct.unpack('<HH', hdr[26:30])
    return info.header_offset + 30 + nlen + elen


def read_entry(path, name):
    with zipfile.ZipFile(path) as z:
        info = z.getinfo(name)
        if info.compress_type == 0:
            return z.read(name)
        with open(path, 'rb') as fp:
            off = _data_off(fp, info)
            fp.seek(off)
            comp = fp.read(info.compress_size)
    if info.compress_type == 93:
        d = zstandard.ZstdDecompressor()
        return d.decompress(comp, max_output_size=info.file_size)
    raise NotImplementedError('compress_type %d' % info.compress_type)


def main():
    cmd = sys.argv[1]
    if cmd == 'list':
        with zipfile.ZipFile(sys.argv[2]) as z:
            for i in z.infolist():
                print('%-34s method=%-3d comp=%-10d size=%d' % (i.filename, i.compress_type,
                                                                i.compress_size, i.file_size))
    elif cmd == 'extract':
        b = read_entry(sys.argv[2], sys.argv[3])
        with open(sys.argv[4], 'wb') as f:
            f.write(b)
        print('%s -> %s (%d B)' % (sys.argv[3], sys.argv[4], len(b)))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
