# -*- coding: utf-8 -*-
r"""fix_zh116_save.py — 只读导出记忆卡里某个存档目录 (默认 BASLUS-20613*)

用法:
  python tools/iso_build/fix_zh116_save.py <Mcd001.ps2> [--name BASLUS-20613] [--out <dir>]
"""
import argparse
import os
import sys

PAGE_RAW = 528
CLUSTER_RAW = PAGE_RAW * 2


def read_cluster(fp, c):
    fp.seek(c * CLUSTER_RAW)
    p0 = fp.read(512)
    fp.seek(c * CLUSTER_RAW + PAGE_RAW)
    p1 = fp.read(512)
    return p0 + p1


def ent(e):
    return dict(mode=int.from_bytes(e[0:4], 'little'),
                length=int.from_bytes(e[4:8], 'little'),
                cluster=int.from_bytes(e[0x10:0x14], 'little'),
                name=e[0x40:0x60].split(b'\x00')[0].decode('ascii', 'replace'),
                raw=e)


def used(mode):
    return mode not in (0, 0xFFFFFFFF) and (mode & 0x8000)


def list_dir(fp, c, count):
    out = []
    for k in range((count + 1) // 2):
        blk = read_cluster(fp, c + k)
        for i in range(2):
            e = ent(blk[i * 512:(i + 1) * 512])
            if used(e['mode']):
                out.append(e)
    return out


def read_chain(fp, c, nbytes):
    data = bytearray()
    cc = c
    while len(data) < nbytes and cc not in (0, 0xFFFFFFFF):
        data += read_cluster(fp, cc)
        cc += 1
    return bytes(data[:nbytes])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mc')
    ap.add_argument('--name', default='BASLUS-20613')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    fp = open(a.mc, 'rb')
    sb = read_cluster(fp, 0)
    root = int.from_bytes(sb[0x3c:0x40], 'little')
    print('superblock: rootdir_cluster=%d alloc_offset=%d clusters_per_card=%d' %
          (root, int.from_bytes(sb[0x34:0x38], 'little'),
           int.from_bytes(sb[0x30:0x34], 'little')))
    roots = list_dir(fp, root, 2)
    print('root dir cluster %d:' % root)
    for e in roots:
        print('   %-24s mode=%08X len=%-5d clu=%d' % (e['name'], e['mode'], e['length'], e['cluster']))

    tgt = [e for e in roots if e['name'].startswith(a.name)]
    if not tgt:
        print('!! 没找到 %s*' % a.name)
        return 1
    for t in tgt:
        print('\n== %s (dir cluster %d, %d entries)' % (t['name'], t['cluster'], t['length']))
        entries = list_dir(fp, t['cluster'], t['length'])
        for e in entries:
            print('   %-20s mode=%08X len=%-8d clu=%-6d' % (e['name'], e['mode'], e['length'], e['cluster']))
            if e['mode'] & 0x20 or e['name'] in ('.', '..'):
                continue
            data = read_chain(fp, e['cluster'], e['length'])
            print('        data %d B  sha1=%s' % (len(data), __import__('hashlib').sha1(data).hexdigest()[:12]))
            if a.out:
                os.makedirs(a.out, exist_ok=True)
                p = os.path.join(a.out, e['name'])
                with open(p, 'wb') as f:
                    f.write(data)
    fp.close()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
