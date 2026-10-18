# -*- coding: utf-8 -*-
r"""fix_zh116_mcwalk.py — 从根目录开始**只走目录树**列 PCSX2 记忆卡内容 (只读)

比 fix_zh116_mc.py 的全盘乱扫干净: 超级块给根目录簇号, 之后只顺着 DIR 项递归。

用法:
  python tools/iso_build/fix_zh116_mcwalk.py <Mcd001.ps2> [--dump <目录>]
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


def entry(e):
    mode = int.from_bytes(e[0:4], 'little')
    length = int.from_bytes(e[4:8], 'little')
    cluster = int.from_bytes(e[0x10:0x14], 'little')
    name = e[0x40:0x60].split(b'\x00')[0]
    return mode, length, cluster, name


def dt(b):
    if len(b) < 8:
        return '?'
    s, mi, h, d, mo = b[1], b[2], b[3], b[4], b[5]
    y = b[6] | (b[7] << 8)
    try:
        return '%04d-%02d-%02d %02d:%02d:%02d' % (y, mo, d, h, mi, s)
    except Exception:
        return '?'


def valid(mode):
    return mode not in (0, 0xFFFFFFFF) and (mode & 0x8000) and (mode & 0x0020)


def walk(fp, c, depth, out, dumpdir, path):
    blk = read_cluster(fp, c)
    for i in range(2):
        e = blk[i * 512:(i + 1) * 512]
        mode, length, cluster, name = entry(e)
        if not valid(mode):
            continue
        nm = name.decode('ascii', 'replace')
        if nm in ('.', '..') and depth == 0:
            continue
        print('%s [%s] clu=%-6d n=%-5d cr=%s mod=%s name=%s' %
              ('  ' * depth, 'DIR ' if (mode & 0x20) else 'FILE', cluster, length,
               dt(e[0x08:0x10]), dt(e[0x18:0x20]), nm))
        full = os.path.join(path, nm)
        if mode & 0x20:
            if nm not in ('.', '..'):
                walk(fp, cluster, depth + 1, out, dumpdir, full)
        else:
            data = bytearray()
            cc, left = cluster, length
            while left > 0 and cc not in (0, 0xFFFFFFFF):
                cl = read_cluster(fp, cc)
                take = min(left, len(cl))
                data += cl[:take]
                left -= take
                cc = int.from_bytes(cl[0:4], 'little') if False else cc + 1
            print('%s    -> %d B' % ('  ' * depth, len(data)))
            if dumpdir:
                os.makedirs(os.path.dirname(os.path.join(dumpdir, full.lstrip('/\\'))),
                            exist_ok=True)
                with open(os.path.join(dumpdir, full.lstrip('/\\')), 'wb') as f:
                    f.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mc')
    ap.add_argument('--dump', default=None)
    a = ap.parse_args()
    with open(a.mc, 'rb') as fp:
        sb = read_cluster(fp, 0)
        root = int.from_bytes(sb[0x00:0x04], 'little')
        print('%s: superblock[0:4]=%08X -> root cluster %d' % (a.mc, root, root))
        # 保险: 超级块字段口径不确定时, 用扫描法找根 (第一个含 '.'/'..' 的簇)
        blk = read_cluster(fp, root)
        m0, _l0, _c0, n0 = entry(blk[0:512])
        if n0.split(b'\x00')[0] != b'.':
            print('  超级块口径不符, 扫描根目录 ...')
            for c in range(1, 16384):
                b = read_cluster(fp, c)
                m0, _l, _c, n0 = entry(b[0:512])
                m1, _l1, _c1, n1 = entry(b[512:1024])
                if n0.split(b'\x00')[0] == b'.' and n1.split(b'\x00')[0] == b'..':
                    root = c
                    print('  root cluster = %d' % c)
                    break
        walk(fp, root, 0, None, a.dump, '')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
