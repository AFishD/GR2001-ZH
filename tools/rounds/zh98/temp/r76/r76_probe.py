# -*- coding: utf-8 -*-
"""r76_probe.py - READ-ONLY helper: CRC identification + .p2s entry listing.

Usage:
  python r76_probe.py crc <file> [nbytes]
  python r76_probe.py list <p2s>
"""
import os
import sys
import zlib

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))


def cmd_crc(path, nbytes=None):
    n = os.path.getsize(path) if not nbytes else min(int(nbytes, 0), os.path.getsize(path))
    c = 0
    with open(path, "rb") as f:
        left = n
        while left > 0:
            b = f.read(min(1 << 20, left))
            if not b:
                break
            c = zlib.crc32(b, c)
            left -= len(b)
    print("%-70s n=%10d crc32=%08X" % (os.path.basename(path), n, c & 0xFFFFFFFF))


def main():
    cmd = sys.argv[1]
    if cmd == "crc":
        cmd_crc(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "list":
        import fix_zh116_p2s as R
        import zipfile
        with zipfile.ZipFile(sys.argv[2]) as z:
            for i in z.infolist():
                print("%-34s method=%-3d comp=%-10d size=%d" %
                      (i.filename, i.compress_type, i.compress_size, i.file_size))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
