# -*- coding: utf-8 -*-
r"""ddump_scan.py —— 扫描 PCSX2 CDVD 块转储，判定各 dump 里是否含 SLUS_206.13（ELF）扇区。

只读：不写任何 ISO / dump；仅在需要时按 --extract 把 ELF 落到本目录 temp\。

用法：
  python ddump_scan.py                       # 列出所有 dump + 是否含 ELF 扇区
  python ddump_scan.py --extract <dump关键词> <out.elf>
  python ddump_scan.py --sha <file> [...]
"""
import glob
import hashlib
import os
import struct
import sys

DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
SEC = 2048
ELF_LBA = 295
ELF_SECTORS = (37453732 + SEC - 1) // SEC   # 18288 → 覆盖 295..18582


def load_index(dump):
    """返回 (lba -> 数据文件偏移 dict, total_lba, filesize)。"""
    n = os.path.getsize(dump)
    with open(dump, 'rb') as f:
        magic, bsz, total, _z = struct.unpack('<4sIII', f.read(16))
    if magic != b'BDV2':
        return None, None, n
    cnt, rem = divmod(n - 16, 4 + SEC)
    idx = {}
    with open(dump, 'rb') as f:
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            lba = struct.unpack('<I', f.read(4))[0]
            idx[lba] = 16 + i * (4 + SEC) + 4
    return idx, total, n


def read_raw(dump, lba, count, idx=None):
    """按 lba→偏移索引（必须传 idx，非连续 dump 才不会读错）。"""
    if idx is None:
        idx, _t, _n = load_index(dump)
    with open(dump, 'rb') as f:
        out = bytearray()
        for i in range(count):
            f.seek(idx[lba + i])
            out += f.read(SEC)
        return bytes(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) > 1 and sys.argv[1] == '--sha':
        for p in sys.argv[2:]:
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''):
                    h.update(b)
            print('%s  %s  %d B' % (h.hexdigest(), p, os.path.getsize(p)))
        return
    if len(sys.argv) > 1 and sys.argv[1] == '--extract':
        key, out = sys.argv[2], sys.argv[3]
        cands = [d for d in sorted(glob.glob(os.path.join(DUMPDIR, '*.dump'))) if key in os.path.basename(d)]
        if len(cands) != 1:
            raise SystemExit('关键词 %r 命中 %d 个 dump：%s' % (key, len(cands), cands))
        d = cands[0]
        idx, total, n = load_index(d)
        miss = [l for l in range(ELF_LBA, ELF_LBA + ELF_SECTORS) if l not in idx]
        if miss:
            raise SystemExit('缺 %d 扇区（例 %s）' % (len(miss), miss[:6]))
        data = read_raw(d, ELF_LBA, ELF_SECTORS, idx)[:37453732]
        if data[:4] != b'\x7fELF':
            raise SystemExit('取回数据不是 ELF（首 4 字节 %r）—— 该盘 ISO 布局与之不同' % data[:4])
        open(out, 'wb').write(data)
        print('[out] %s  %d B  ← %s' % (out, len(data), os.path.basename(d)))
        return
    print('dumpdir = %s' % DUMPDIR)
    print('ELF LBA = %d..%d (%d 扇区)' % (ELF_LBA, ELF_LBA + ELF_SECTORS - 1, ELF_SECTORS))
    print()
    print('%-56s %10s %7s %9s %s' % ('dump', 'size', 'sectors', '覆盖%', 'ELF 扇区'))
    rows = []
    for d in sorted(glob.glob(os.path.join(DUMPDIR, '*.dump'))):
        idx, total, n = load_index(d)
        if idx is None:
            rows.append((os.path.basename(d), n, -1, -1, '不是 BDV2'))
            continue
        have = sum(1 for l in range(ELF_LBA, ELF_LBA + ELF_SECTORS) if l in idx)
        rows.append((os.path.basename(d), n, len(idx), 100.0 * len(idx) / total, '%d/%d' % (have, ELF_SECTORS)))
    for r in rows:
        print('%-56s %10d %7s %8s%% %s' % r)
    print()
    ok = [r[0] for r in rows if isinstance(r[4], str) and r[4].endswith('/%d' % ELF_SECTORS)]
    print('含完整 ELF 的 dump（%d 个）：' % len(ok))
    for k in ok:
        print('   ', k)


if __name__ == '__main__':
    main()
