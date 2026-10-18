# -*- coding: utf-8 -*-
r"""fix_zh116_mclist.py — 列记忆卡目录树 (修正版: 实际簇号 = 条目簇号 + alloc_offset)

用法: python tools/iso_build/fix_zh116_mclist.py <Mcd001.ps2> [--dump <dir>] [--only BASLUS-20613]
输出写成 UTF-8 文件时请用 --out (控制台是 GBK, 中文标题会炸)。
"""
import argparse
import hashlib
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
                dt_cr=e[0x08:0x10], dt_mod=e[0x18:0x20],
                name=e[0x40:0x60].split(b'\x00')[0],
                title=e[0x60:0x160].split(b'\x00')[0])


def used(mode):
    return mode not in (0, 0xFFFFFFFF) and (mode & 0x8000)


def dt(b):
    if len(b) < 8:
        return '?'
    return '%04d-%02d-%02d %02d:%02d:%02d' % (b[6] | (b[7] << 8), b[5], b[4], b[3], b[2], b[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mc')
    ap.add_argument('--dump', default=None)
    ap.add_argument('--only', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    lines = []

    def P(s):
        lines.append(s)

    fp = open(a.mc, 'rb')
    sb = read_cluster(fp, 0)
    ao = int.from_bytes(sb[0x34:0x38], 'little')
    root = int.from_bytes(sb[0x3c:0x40], 'little') + ao
    P('%s  alloc_offset=%d rootdir_cluster(card)=%d' % (a.mc, ao, root))

    def walk(card_clu, count, depth, path):
        for k in range((count + 1) // 2):
            blk = read_cluster(fp, card_clu + k)
            for i in range(2):
                e = ent(blk[i * 512:(i + 1) * 512])
                if not used(e['mode']):
                    continue
                nm = e['name'].decode('ascii', 'replace')
                if nm in ('.', '..'):
                    continue
                title = e['title'].decode('gbk', 'replace')
                isdir = bool(e['mode'] & 0x20)
                P('%s[%s] clu=%-6d len=%-8d cr=%s mod=%s name=%s | title=%s'
                  % ('  ' * depth, 'DIR ' if isdir else 'FILE', e['cluster'],
                     e['length'], dt(e['dt_cr']), dt(e['dt_mod']), nm, title[:40]))
                full = os.path.join(path, nm)
                if isdir:
                    walk(e['cluster'] + ao, e['length'], depth + 1, full)
                else:
                    data = bytearray()
                    cc = e['cluster'] + ao
                    while len(data) < e['length'] and cc not in (0, 0xFFFFFFFF):
                        data += read_cluster(fp, cc)
                        cc += 1
                    data = bytes(data[:e['length']])
                    P('%s    data %d B sha1=%s' % ('  ' * depth, len(data),
                                                   hashlib.sha1(data).hexdigest()[:12]))
                    if a.dump:
                        p = os.path.join(a.dump, full.lstrip('/\\'))
                        os.makedirs(os.path.dirname(p), exist_ok=True)
                        open(p, 'wb').write(data)

    bc = ent(read_cluster(fp, root)[0:512])['length']
    P('root entries: %d' % bc)
    if a.only:
        for k in range((bc + 1) // 2):
            blk = read_cluster(fp, root + k)
            for i in range(2):
                e = ent(blk[i * 512:(i + 1) * 512])
                if not used(e['mode']):
                    continue
                nm = e['name'].decode('ascii', 'replace')
                if nm.startswith(a.only) and (e['mode'] & 0x20):
                    P('[DIR] %s clu=%d len=%d cr=%s mod=%s'
                      % (nm, e['cluster'], e['length'], dt(e['dt_cr']), dt(e['dt_mod'])))
                    walk(e['cluster'] + ao, e['length'], 1, nm)
                elif nm.startswith(a.only):
                    P('[FILE] %s clu=%d len=%d mod=%s' % (nm, e['cluster'], e['length'], dt(e['dt_mod'])))
    else:
        walk(root, bc, 0, '')
    fp.close()

    txt = '\n'.join(lines) + '\n'
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(txt)
        print('written %s (%d lines)' % (a.out, len(lines)))
    else:
        sys.stdout.write(txt)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
