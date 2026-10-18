# -*- coding: utf-8 -*-
r"""cave_extract_elf.py -- pull SLUS_206.13 out of an ISO (READ-ONLY) into r79/dump/.

The PS2 executable sits at LBA 295 as a raw file (37,453,732 B); the ELF PT_LOAD[0]
starts at file offset 0x80 and maps VA 0x00100000.  Everything the cave audit quotes
is inside that first segment, so byte identity of this file with the retail copy is the
whole basis of the comparison.

usage: python cave_extract_elf.py <iso> <out.bin>
"""
import hashlib
import os
import sys

ELF_LBA = 295
ELF_BYTES = 37453732


def main():
    iso, out = sys.argv[1], sys.argv[2]
    with open(iso, "rb") as f:
        f.seek(ELF_LBA * 2048)
        blob = f.read(ELF_BYTES)
    assert len(blob) == ELF_BYTES, len(blob)
    assert blob[:4] == b"\x7fELF", blob[:4].hex()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as g:
        g.write(blob)
    print("%s -> %s  %d B  sha256=%s" % (iso, out, len(blob),
                                        hashlib.sha256(blob).hexdigest()))


if __name__ == "__main__":
    main()
