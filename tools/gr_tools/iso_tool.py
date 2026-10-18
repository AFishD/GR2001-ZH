#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iso_tool.py - PS2 ISO9660 镜像解析 / 列表 / 提取 / 重建 工具

用法:
  python iso_tool.py list   <iso>                     列出镜像内所有文件
  python iso_tool.py extract <iso> <outdir> [pattern] 提取全部(或匹配 pattern 的)文件
  python iso_tool.py build  <srcdir> <out.iso>        从目录重建 ISO9660 镜像(PS2 可用)
"""
import os, sys, struct, fnmatch

SECTOR = 2048

class IsoNode:
    def __init__(self):
        self.lba = 0
        self.size = 0
        self.name = ""
        self.is_dir = False
        self.children = []
        self.path = ""

def parse_record(data, off, ucs=False):
    ln = data[off]
    if ln == 0:
        return None
    ext_attr = struct.unpack_from('<H', data, off + 1)[0]
    size = struct.unpack_from('<I', data, off + 10)[0]
    lba = struct.unpack_from('<I', data, off + 2)[0]
    flags = data[off + 25]
    name_len = data[off + 32]
    raw = data[off + 33: off + 33 + name_len]
    if ucs:
        name = raw.decode('utf-16-be', 'replace').rstrip('\u0000')
    else:
        name = raw.decode('latin-1', 'replace')
        if name.endswith('.'):
            name = name[:-1]
        if ';' in name:
            name = name.rsplit(';', 1)[0]
    is_dir = bool(flags & 2)
    rec = IsoNode()
    rec.lba, rec.size, rec.name, rec.is_dir = lba, size, name, is_dir
    return ln, rec

def scan_dir(f, lba, size, ucs, parent_path):
    f.seek(lba * SECTOR)
    data = f.read(size)
    out, off = [], 0
    while off < len(data):
        r = parse_record(data, off, ucs)
        if r is None:
            off = (off // SECTOR + 1) * SECTOR
            continue
        ln, rec = r
        off += ln
        if rec.name in ('\x00', '\u0000', '\x01', '.'):
            continue
        rec.path = parent_path + rec.name + ('/' if rec.is_dir else '')
        out.append(rec)
    return out

def walk(f, node, ucs, parent):
    kids = scan_dir(f, node.lba, node.size, ucs, parent.path)
    for k in kids:
        node.children.append(k)
        if k.is_dir:
            walk(f, k, ucs, k)

def parse_iso(path):
    f = open(path, 'rb')
    root, ucs = None, False
    sector = 16
    while True:
        f.seek(sector * SECTOR)
        d = f.read(SECTOR)
        if len(d) < SECTOR or d[1:6] != b'CD001':
            break
        vtype = d[0]
        if vtype == 1 and root is None:
            root = parse_record(d, 156, False)[1]
        elif vtype == 2:
            esc = d[88:120]
            if b'%/@' in esc:          # Joliet UCS-2
                root = parse_record(d, 156, True)[1]
                ucs = True
        elif vtype == 255:
            break
        sector += 1
    if root is None:
        raise SystemExit('未找到 ISO9660 主卷描述符')
    walk(f, root, ucs, IsoNode())
    return f, root

def flatten(root):
    files = []
    def rec(n):
        for c in n.children:
            if c.is_dir:
                rec(c)
            else:
                files.append(c)
    rec(root)
    return files

def cmd_list(iso):
    f, root = parse_iso(iso)
    def rec(n, depth):
        for c in sorted(n.children, key=lambda x: (not x.is_dir, x.name.lower())):
            tag = '<DIR>' if c.is_dir else '%10d' % c.size
            print('%s%-52s LBA=%-9d size=%s' % ('  ' * depth, c.path, c.lba, tag))
            if c.is_dir:
                rec(c, depth + 1)
    rec(root, 0)
    files = flatten(root)
    print('\n共 %d 个文件' % len(files))

def cmd_extract(iso, outdir, pattern='*'):
    f, root = parse_iso(iso)
    files = flatten(root)
    n = 0
    for c in files:
        rel = c.path
        if not fnmatch.fnmatch(rel.lower(), pattern.lower()) and \
           not fnmatch.fnmatch(os.path.basename(rel).lower(), pattern.lower()):
            continue
        dst = os.path.join(outdir, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        f.seek(c.lba * SECTOR)
        left = c.size
        with open(dst, 'wb') as o:
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                o.write(chunk)
                left -= len(chunk)
        n += 1
        print('提取 %s (%d 字节)' % (rel, c.size))
    print('完成: %d/%d 个文件' % (n, len(files)))

# ---------- rebuild ----------
def build_iso(srcdir, outiso):
    """从目录构建 PS2 可读的 ISO9660 镜像(模式1/2048字节扇区)"""
    entries = []  # (relpath, fullpath, size) ; dirs = (None标记)
    dirs = []
    for root, dnames, fnames in os.walk(srcdir):
        rel = os.path.relpath(root, srcdir).replace(os.sep, '/')
        if rel == '.':
            rel = ''
        dirs.append(rel)
        for fn in fnames:
            entries.append((rel + '/' + fn if rel else fn,
                            os.path.join(root, fn)))
    entries.sort(key=lambda e: e[0])

    # 布局: 扇区16=PVD,17=终止符,之后根目录/文件按序
    cur = 18
    def pad():
        nonlocal cur
        cur = (cur + 15) // 16 * 16 if False else cur  # 不做额外对齐,ISO9660无硬性要求
    # 目录记录区: 先为每个目录分配
    dir_recs = {}
    def dir_size(nkids, name_bytes_total):
        # 粗略: 每条记录 33+name, 目录内容按扇区向上取整
        raw = 0
        for nb in name_bytes_total:
            raw += (34 + len(nb) + 1) & ~1
        raw += 34 + 1 + 1  # . 和 .. 两条
        return max(1, (raw + SECTOR - 1) // SECTOR)

    all_names = {}
    for d in dirs:
        kids = []
        for e in entries:
            parent, _ = e[0].rsplit('/', 1) if '/' in e[0] else ('', e[0])
            if parent == d and '/' not in e[0].rstrip('/'):
                pass
        all_names[d] = kids
    def parent_of(rel):
        return rel.rsplit('/', 1)[0] if '/' in rel else ''
    # 1) 收集每个目录的直接子项
    subdirs = {}
    subfiles = {}
    for d in dirs:
        subdirs[d] = [x for x in dirs if x != '' and parent_of(x) == d]
        subfiles[d] = [e[0] for e in entries if parent_of(e[0]) == d]

    # 2) 为目录内容预留 LBA
    dir_lba = {}
    for d in dirs:
        nb = [x.rsplit('/', 1)[-1].encode('ascii', 'replace') for x in subdirs[d]] + \
             [x.rsplit('/', 1)[-1].encode('ascii', 'replace') + b';1' for x in subfiles[d]]
        nsec = dir_size(subdirs[d], nb)
        dir_lba[d] = cur
        cur += nsec
    # 3) 文件数据 LBA
    file_lba = {}
    for rel, full in entries:
        file_lba[rel] = cur
        cur += max(1, (os.path.getsize(full) + SECTOR - 1) // SECTOR)
    total = cur

    def rec_bytes(name, lba, size, is_dir, hidden_ver=True):
        if name == '.':
            nb = b'\x00'
        elif name == '..':
            nb = b'\x01'
        else:
            nb = name.encode('ascii', 'replace')
        if not is_dir and hidden_ver:
            nb += b';1'
        ln = 34 + len(nb)
        if ln % 2:
            ln += 1
        b = bytearray(ln)
        struct.pack_into('<I', b, 2, lba)
        struct.pack_into('>I', b, 6, lba)
        struct.pack_into('<I', b, 10, size)
        struct.pack_into('>I', b, 14, size)
        b[25] = 2 if is_dir else 0
        b[0] = ln
        struct.pack_into('<I', b, 28, 1)
        b[32] = len(nb)
        b[33:33 + len(nb)] = nb
        return bytes(b)

    def build_dir_content(d):
        cont = bytearray()
        self_rec = rec_bytes('\x00' if False else '.', dir_lba[d],
                             SECTOR * dir_size(subdirs[d], [b''] * max(1, len(subdirs[d]) + len(subfiles[d]))) , True)
        # 修正: . 与 .. 的 size 用自身目录实际大小,先占位再回填
        cont += rec_bytes('.', dir_lba[d], 0, True)
        pd = parent_of(d)
        cont += rec_bytes('..', dir_lba.get(pd, dir_lba['']), 0, True)
        for sd in subdirs[d]:
            cont += rec_bytes(sd.rsplit('/', 1)[-1], dir_lba[sd],
                              SECTOR, True)
        for fn in subfiles[d]:
            full = os.path.join(srcdir, fn.replace('/', os.sep))
            cont += rec_bytes(fn.rsplit('/', 1)[-1], file_lba[fn],
                              os.path.getsize(full), False)
        nsec = max(1, (len(cont) + SECTOR - 1) // SECTOR)
        cont += b'\x00' * (nsec * SECTOR - len(cont))
        return bytes(cont), nsec

    contents = {d: build_dir_content(d) for d in dirs}
    # 回填目录自身 size
    def rebuild(d):
        cont = bytearray(contents[d][0])
        self_size = contents[d][1] * SECTOR
        r1 = rec_bytes('.', dir_lba[d], self_size, True)
        pd = parent_of(d)
        r2 = rec_bytes('..', dir_lba.get(pd, dir_lba['']),
                       contents.get(pd, (None, 1))[1] * SECTOR if pd in contents else SECTOR, True)
        cont[0:len(r1)] = r1
        cont[len(r1):len(r1) + len(r2)] = r2
        return bytes(cont), contents[d][1]
    contents = {d: rebuild(d) for d in dirs}

    # PVD
    pvd = bytearray(SECTOR)
    pvd[0] = 1
    pvd[1:6] = b'CD001'
    pvd[6] = 1
    pvd[8:40] = b'PLAYSTATION'.ljust(32)
    pvd[40:72] = b'PS2_REBUILD'.ljust(32)
    struct.pack_into('<I', pvd, 80, total)
    struct.pack_into('>I', pvd, 84, total)
    pvd[120:124] = struct.pack('<H', 1) * 2
    pvd[156:190] = rec_bytes('.', dir_lba[''], contents[''][1] * SECTOR, True)[:34]
    pvd[313] = 1  # 卷集合大小
    pvd[317] = 1
    pvd[813:814] = b'\x00'
    tm = bytearray(b'2026090400000000\x00')
    pvd[813:830] = b'2026090400000000\x00'
    pvd[845:862] = b'2026090400000000\x00'

    with open(outiso, 'wb') as o:
        # 前16扇区留空(PS2 兼容)
        for s in range(16):
            o.write(b'\x00' * SECTOR)
        o.write(pvd)
        def vd(typ, std):
            v = bytearray(SECTOR)
            v[0] = typ; v[1:6] = std; v[6] = 1
            return bytes(v)
        o.write(vd(255, b'CD001'))   # 终止符(版本1)
        # 注: BEA01/NSR02/TEA01 序列会使 PS2 BIOS 引导卡死, 不写
        for d in dirs:
            o.write(contents[d][0])
        for rel, full in entries:
            sz = os.path.getsize(full)
            with open(full, 'rb') as fi:
                left = sz
                while left > 0:
                    chunk = fi.read(min(1 << 20, left))
                    o.write(chunk)
                    left -= len(chunk)
            pad_bytes = (SECTOR - sz % SECTOR) % SECTOR
            if pad_bytes:
                o.write(b'\x00' * pad_bytes)
    print('已生成 %s (%d 扇区, %.2f MB)' % (outiso, total, total * SECTOR / 1048576.0))

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'list':
        cmd_list(sys.argv[2])
    elif cmd == 'extract':
        cmd_extract(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '*')
    elif cmd == 'build':
        build_iso(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
