# -*- coding: utf-8 -*-
r"""cvar_diff.py — 严格逐字节差异区间提取 (EN_ORIG vs ZH113b) + 结构映射

用法:
    python cvar_diff.py --a <EN.iso> --b <ZH.iso> --out <diff.json> [--maxruns N]

产出:
    runs: 精确差异区间 [(start, end)] —— 相邻 1 字节间隔的区间会合并
    runs_coarse: 同一批区间按 gap 合并成大块 (便于阅读)
每个区间附上落在哪个已解析的结构内 (ELF / MENU.IMG / GR.IMG / ISO9660 目录 / 其它 IMG)。
"""
import argparse
import hashlib
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048


def parse_iso9660_pvd(fh):
    fh.seek(16 * SEC)
    pvd = fh.read(SEC)
    assert pvd[0] == 1 and pvd[1:6] == b'CD001', 'not iso9660'
    root = pvd[156:156 + 34]
    return {
        'root_lba': struct.unpack('<I', root[2:6])[0],
        'root_size': struct.unpack('<I', root[10:14])[0],
        'vol_space_size': struct.unpack('<I', pvd[80:84])[0],
        'volume_id': pvd[40:72].decode('ascii', 'replace').strip(),
    }


def walk_dir(fh, lba, size, out, prefix=''):
    """遍历 ISO9660 目录树, out: list of dict(name, lba, size, iso, dirrecord_iso)"""
    fh.seek(lba * SEC)
    data = fh.read(size)
    off = 0
    while off < len(data):
        rec_len = data[off]
        if rec_len == 0:
            # 跳到下一扇区边界
            nxt = ((off // SEC) + 1) * SEC
            if nxt <= off:
                break
            off = nxt
            continue
        rec = data[off:off + rec_len]
        ext_lba = struct.unpack('<I', rec[2:6])[0]
        ext_size = struct.unpack('<I', rec[10:14])[0]
        flags = rec[25]
        name_len = rec[32]
        raw = rec[33:33 + name_len]
        if name_len == 1 and raw in (b'\x00', b'\x01'):
            name = '.' if raw == b'\x00' else '..'
        else:
            name = raw.decode('ascii', 'replace')
            if name.endswith(';1'):
                name = name[:-2]
        full = (prefix + '/' + name) if prefix else name
        out.append({
            'name': full,
            'lba': ext_lba,
            'size': ext_size,
            'iso_off': ext_lba * SEC,
            'iso_end': ext_lba * SEC + ext_size,
            'is_dir': bool(flags & 2),
            'dirrec_iso': lba * SEC + off,
            'dirrec_len': rec_len,
        })
        if flags & 2 and name not in ('.', '..'):
            walk_dir(fh, ext_lba, ext_size, out, full)
        off += rec_len
    return out


def find_runs(fa, fb, n, chunk=1 << 22):
    """返回精确差异 1-字节游程 [start, end)"""
    runs = []
    off = 0
    while off < n:
        k = min(chunk, n - off)
        da = fa.read(k)
        db = fb.read(k)
        if da == db:
            off += k
            continue
        # 在此块内找游程
        i = 0
        while i < k:
            if da[i] == db[i]:
                i += 1
                continue
            j = i + 1
            while j < k and da[j] != db[j]:
                j += 1
            s, e = off + i, off + j
            if runs and runs[-1][1] >= s:
                runs[-1][1] = max(runs[-1][1], e)
            else:
                runs.append([s, e])
            i = j
        off += k
    return runs


def merge_coarse(runs, gap):
    out = []
    for s, e in runs:
        if out and s - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def sha256_file(p, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--coarse-gap', type=int, default=65536)
    x = ap.parse_args()

    sa, sb = os.path.getsize(x.a), os.path.getsize(x.b)
    print('A = %s  %d B  sha256=%s' % (x.a, sa, sha256_file(x.a)))
    print('B = %s  %d B  sha256=%s' % (x.b, sb, sha256_file(x.b)))
    print('size delta = %d' % (sb - sa))

    with open(x.a, 'rb') as fa:
        pvd = parse_iso9660_pvd(fa)
        files = []
        walk_dir(fa, pvd['root_lba'], pvd['root_size'], files)
    print('ISO9660: volume_id=%r vol_space=%d root_lba=%d files=%d'
          % (pvd['volume_id'], pvd['vol_space_size'], pvd['root_lba'], len(files)))

    n = min(sa, sb)
    with open(x.a, 'rb') as fa, open(x.b, 'rb') as fb:
        runs = find_runs(fa, fb, n)
    coarse = merge_coarse(runs, x.coarse_gap)
    tot = sum(e - s for s, e in runs)
    print('★ 精确差异游程 %d 个, 合计 %d B (%.6f%%)'
          % (len(runs), tot, 100.0 * tot / max(1, n)))
    print('★ 合并后 (gap<=%d) 大块 %d 个, 合计 %d B'
          % (x.coarse_gap, len(coarse), sum(e - s for s, e in coarse)))

    # 归属
    def owner(off):
        for f in files:
            if f['iso_off'] <= off < f['iso_end']:
                return f['name']
        return None

    res = {
        'a': x.a, 'b': x.b, 'size_a': sa, 'size_b': sb,
        'sha256_a': sha256_file(x.a), 'sha256_b': sha256_file(x.b),
        'iso9660': pvd,
        'files': files,
        'runs': runs,
        'coarse': coarse,
    }
    with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1)

    # 归属统计 (按粗块, 用块内每个 run 的中点)
    by = {}
    for s, e in runs:
        mid = (s + e) // 2
        o = owner(mid) or '<未归属/结构区>'
        d = by.setdefault(o, [0, 0, s, e])
        d[0] += 1
        d[1] += e - s
        d[2] = min(d[2], s)
        d[3] = max(d[3], e)
    print('\n== 差异归属 (按 ISO9660 文件) ==')
    for name in sorted(by, key=lambda k: -by[k][1]):
        c, b, lo, hi = by[name]
        print('  %-28s runs=%-6d bytes=%-10d 0x%09X..0x%09X' % (name, c, b, lo, hi))

    print('\n== 粗块 前 60 ==')
    for s, e in coarse[:60]:
        print('  0x%09X..0x%09X %10d B  mid_owner=%s'
              % (s, e, e - s, owner((s + e) // 2) or '-'))
    if len(coarse) > 60:
        print('  ... 还有 %d 块' % (len(coarse) - 60))
    print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
