# -*- coding: utf-8 -*-
r"""probe_base.py —— 只读体检：把基底盘的 ELF 抽出来存证（sha256 / 尺寸 / LBA / PT_LOAD）。
用法: python work\builds\GR_DFIX\tools\probe_base.py <iso> [<out_elf>]
"""
import hashlib
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'GR_DISASM', 'tools'))
import dfix_apply as D  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    iso = sys.argv[1]
    out_elf = sys.argv[2] if len(sys.argv) > 2 else None
    data, lba, size = D.read_elf_from_iso(iso)
    va2off, segs = D.va_map(data)
    line, gates, geom = D.lineage(data, va2off)
    rec = dict(iso=os.path.abspath(iso),
               iso_bytes=os.path.getsize(iso),
               elf_lba=lba,
               elf_bytes=size,
               elf_sha256=hashlib.sha256(data).hexdigest(),
               pt_load=[(hex(v), hex(o), hex(s)) for (v, o, s) in segs],
               lineage=line,
               gates=['0x%04X' % g for g in gates],
               atlas_geom=dict(ncol=geom[0], row_shift=geom[1], v0=geom[2], v1=geom[3]))
    print(json.dumps(rec, indent=1, ensure_ascii=False))
    if out_elf:
        with open(out_elf, 'wb') as f:
            f.write(data)
        print('ELF 已写出: %s (%d B)' % (out_elf, len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
