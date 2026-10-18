# -*- coding: utf-8 -*-
r"""fix_zh116_mc.py — 只读列出 PCSX2 记忆卡 (.ps2, 8MB + ECC) 的目录项

布局 (pcsx2/SIO/Memcard/MemoryCardFolder.h):
  page = 512 data + 16 ECC = 528 B;  cluster = 2 page = 1056 B;  card = 16384 page
  目录项 = 512 B: mode@0x00 length@0x04 timeCreated@0x08 cluster@0x10 dirEntry@0x14
                 timeModified@0x18 attr@0x20 pad@0x24(-0x40) name@0x40[32] title@0x60(SJIS)

用法: python tools/iso_build/fix_zh116_mc.py <Mcd001.ps2>
"""
import io
import os
import sys

PAGE_RAW = 528
CLUSTER_RAW = PAGE_RAW * 2
TOTAL_PAGES = 16384


def cluster_bytes(fp, c):
    fp.seek(c * CLUSTER_RAW)
    p0 = fp.read(512)
    fp.seek(c * CLUSTER_RAW + PAGE_RAW)
    p1 = fp.read(512)
    return p0 + p1


def parse_dt(b):
    # u8 unused, sec, min, hour, day, month, u16 year  (BCD-ish / plain)
    if len(b) < 8:
        return '?'
    unused, s, mi, h, d, mo = b[0], b[1], b[2], b[3], b[4], b[5]
    y = b[6] | (b[7] << 8)
    return '%04d-%02d-%02d %02d:%02d:%02d' % (y, mo, d, h, mi, s)


def dec_name(raw):
    return raw.split(b'\x00')[0].decode('ascii', 'replace')


def dec_title(raw):
    raw = raw.split(b'\x00')[0]
    for enc in ('shift_jis', 'gbk', 'latin1'):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.hex()


def main():
    mc = sys.argv[1]
    with open(mc, 'rb') as fp:
        size = os.path.getsize(mc)
        print('%s  %d B (= %d clusters raw)' % (mc, size, size // CLUSTER_RAW))
        n = size // CLUSTER_RAW
        for c in range(min(n, TOTAL_PAGES)):
            blk = cluster_bytes(fp, c)
            for i in range(2):
                e = blk[i * 512:(i + 1) * 512]
                if len(e) < 512:
                    continue
                mode = int.from_bytes(e[0:4], 'little')
                if mode in (0, 0xFFFFFFFF) or not (mode & 0x8000):
                    continue
                length = int.from_bytes(e[4:8], 'little')
                cluster = int.from_bytes(e[0x10:0x14], 'little')
                name = dec_name(e[0x40:0x60])
                title = dec_title(e[0x60:0x160])
                kind = 'DIR ' if (mode & 0x20) else 'FILE'
                print('  c%-5d e%d %s mode=%08X len=%-9d clu=%-6d cr=%s mod=%s name=%-24s title=%s'
                      % (c, i, kind, mode, length, cluster,
                         parse_dt(e[0x08:0x10]), parse_dt(e[0x18:0x20]), name, title[:60]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
