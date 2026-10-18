# -*- coding: utf-8 -*-
r"""fix_zh116_mcscan.py — 逐页扫记忆卡目录项 (不依赖 FAT 链接) + 导出指定存档

用法:
  python tools/iso_build/fix_zh116_mcscan.py <Mcd001.ps2> [--list] [--dump-prefix BASLUS-20613 --out <dir>]
"""
import argparse
import hashlib
import os
import sys

PAGE_RAW = 528


def read_page(fp, pg):
    fp.seek(pg * PAGE_RAW)
    return fp.read(512)


def parse(e):
    mode = int.from_bytes(e[0:4], 'little')
    if mode in (0, 0xFFFFFFFF) or not (mode & 0x8000):
        return None
    name = e[0x40:0x60].split(b'\x00')[0]
    if not name or not all(32 <= c < 127 for c in name):
        return None
    return dict(mode=mode, length=int.from_bytes(e[4:8], 'little'),
                cluster=int.from_bytes(e[0x10:0x14], 'little'),
                name=name.decode('ascii'), title=e[0x60:0x100].split(b'\x00')[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mc')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--dump-prefix', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    size = os.path.getsize(a.mc)
    npages = size // PAGE_RAW
    seen = set()
    rows = []
    with open(a.mc, 'rb') as fp:
        for pg in range(npages):
            e = parse(read_page(fp, pg))
            if not e:
                continue
            key = (e['name'], e['cluster'], e['mode'], e['length'])
            if key in seen:
                continue
            seen.add(key)
            e['page'] = pg
            rows.append(e)
        if a.list:
            for e in rows:
                kind = 'DIR ' if (e['mode'] & 0x20) else 'FILE'
                t = e['title'].decode('gbk', 'replace')
                print('pg%-6d %s mode=%08X len=%-8d clu=%-6d %-24s %s'
                      % (e['page'], kind, e['mode'], e['length'], e['cluster'], e['name'], t[:30]))
        if a.dump_prefix:
            os.makedirs(a.out or '.', exist_ok=True)
            for e in rows:
                if not e['name'].startswith(a.dump_prefix) or (e['mode'] & 0x20):
                    continue
                data = bytearray()
                cc = e['cluster'] + 41
                while len(data) < e['length'] and cc < npages // 2:
                    data += read_page(fp, cc * 2) + read_page(fp, cc * 2 + 1)
                    cc += 1
                data = bytes(data[:e['length']])
                p = os.path.join(a.out or '.', '%s_%d.bin' % (e['name'], e['page']))
                open(p, 'wb').write(data)
                print('dumped %s (%d B) sha1=%s' % (p, len(data), hashlib.sha1(data).hexdigest()[:12]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
