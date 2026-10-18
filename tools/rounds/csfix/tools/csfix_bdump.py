# -*- coding: utf-8 -*-
r"""csfix_bdump.py —— PCSX2 CDVD 块转储（BDV2）解析 + K2 盘内文件抽取（全程只读）。

**为什么有这个工具**：`work\builds\**` 下的 ISO 产物被外部清理删除（2026-10-17 15:19 前后），
但 PCSX2 的 CDVD BlockDump（`%LOCALAPPDATA%\PCSX2\cdvd-dump\*.dump`）**幸存**，
其中 `GR_FA2400_K2 (2026-10-17 15-08-20).dump` 是当天 15:08 起对 `GR_FA2400_K2.iso` 的一次
实跑所读到的**原始扇区拷贝** ⇒ 可以据此取回 K2 盘的 ELF / 容器扇区，
把"逐处反汇编确认 + 可达性 + 文本位点"的判定做在**真盘的字节**上。

BDV2 格式（本工具实测反推，已用文件长度整除自检）：
    off 0   : b"BDV2"
    off 4   : u32 block_size      = 2048
    off 8   : u32 total_lba       = 804768   （== ISO 扇区总数）
    off 12  : u32 = 0
    off 16  : N × [ u32 lba ][ 2048 B ]
    自检：16 + N*2052 == filesize

用法：
  python csfix_bdump.py info
  python csfix_bdump.py ls <lba>
  python csfix_bdump.py dir                     # 只从**原盘 ISO** 读 ISO9660 目录（各盘目录零差异）
  python csfix_bdump.py extract <name> <out>    # 从 dump 里按 ISO9660 目录抽文件
  python csfix_bdump.py sectors <lba> <n> <out> # 直接抽 n 个扇区
"""
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
DUMP = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                    'PCSX2', 'cdvd-dump', 'GR_FA2400_K2 (2026-10-17 15-08-20).dump')
ORIG = os.path.join(ROOT, 'third_party', 'orig', 'ps2',
                    "Tom Clancy's Ghost Recon (USA).iso")
SEC = 2048


# ─────────────────────────── BDV2 ───────────────────────────
def load_index(dump=DUMP):
    """返回 (index dict lba→文件偏移, total_lba, len)。只读。"""
    n = os.path.getsize(dump)
    with open(dump, 'rb') as f:
        hdr = f.read(16)
        magic, bsz, total, zero = struct.unpack('<4sIII', hdr)
        if magic != b'BDV2':
            raise SystemExit('不是 BDV2：%r' % magic)
        if bsz != SEC:
            raise SystemExit('block_size=%d ≠ 2048' % bsz)
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            raise SystemExit('长度自检失败：16 + N*2052 余 %d' % rem)
        idx = {}
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            lba = struct.unpack('<I', f.read(4))[0]
            idx[lba] = 16 + i * (4 + SEC) + 4
    return idx, total, n


def read_sectors(idx, lba, count, dump=DUMP):
    """按 LBA 连续读取 count 个扇区；缺失返回 None。"""
    if not all((lba + i) in idx for i in range(count)):
        return None
    out = bytearray()
    with open(dump, 'rb') as f:
        for i in range(count):
            f.seek(idx[lba + i])
            out += f.read(SEC)
    return bytes(out)


# ─────────────────────── ISO9660（原盘） ───────────────────────
def iso_dir(iso=ORIG):
    """极简 ISO9660 目录遍历：返回 {NAME_UPPER: (lba, size, is_dir)}。只读。"""
    out = {}
    with open(iso, 'rb') as f:
        def sec(n):
            f.seek(n * SEC)
            return f.read(SEC)
        pvd = sec(16)
        if pvd[1:6] != b'CD001':
            raise SystemExit('原盘 sector16 不是 PVD')
        root = pvd[156:156 + 34]
        rlba = struct.unpack_from('<I', root, 2)[0]
        rsize = struct.unpack_from('<I', root, 10)[0]

        def walk(lba, size, prefix=''):
            data = b''
            for i in range((size + SEC - 1) // SEC):
                data += sec(lba + i)
            off = 0
            while off < len (data):
                ln = data[off]
                if ln == 0:
                    off = (off // SEC + 1) * SEC
                    if off >= len(data):
                        break
                    continue
                rec = data[off:off + ln]
                ext = struct.unpack_from('<I', rec, 2)[0]
                sz = struct.unpack_from('<I', rec, 10)[0]
                flags = rec[25]
                nlen = rec[32]
                name = rec[33:33 + nlen].decode('latin-1')
                if name not in ('\x00', '\x01'):
                    nm = (prefix + '/' + name) if prefix else name
                    out[nm.upper()] = (ext, sz, bool(flags & 2))
                    if flags & 2 and nm.count('/') < 3:
                        walk(ext, sz, nm)
                off += ln
        walk(rlba, rsize)
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'info'
    if cmd == 'info':
        idx, total, n = load_index()
        print('dump      = %s' % DUMP)
        print('size      = %d B ; total_lba(头) = %d ; 实收扇区 = %d (%.2f%%)'
              % (n, total, len(idx), 100.0 * len(idx) / total))
        lb = sorted(idx)
        print('lba 范围  = %d .. %d' % (lb[0], lb[-1]))
        # 连续段
        runs = []
        s = p = lb[0]
        for x in lb[1:]:
            if x == p + 1:
                p = x
            else:
                runs.append((s, p))
                s = p = x
        runs.append((s, p))
        print('连续段    = %d 段；最长 8 段：' % len(runs))
        for a, b in sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:8]:
            print('    %7d..%-7d  (%d 扇区, %.1f MB)' % (a, b, b - a + 1,
                                                         (b - a + 1) * SEC / 1048576.0))
    elif cmd == 'sectors':
        lba, cnt, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        idx, _t, _n = load_index()
        d = read_sectors(idx, lba, cnt)
        if d is None:
            miss = [l for l in range(lba, lba + cnt) if l not in idx]
            raise SystemExit('缺扇区 %d 个（例 %s）' % (len(miss), miss[:8]))
        open(out, 'wb').write(d)
        print('[out] %s  %d B（LBA %d..%d）' % (out, len(d), lba, lba + cnt - 1))
    elif cmd == 'dir':
        d = iso_dir()
        print('原盘 ISO9660 条目 %d 个（各盘目录零差异，可直接用于 K2）：' % len(d))
        for k in sorted(d):
            lba, sz, isd = d[k]
            print('  %-52s lba=%-7d size=%-10d %s' % (k, lba, sz, 'DIR' if isd else ''))
    elif cmd == 'extract':
        name, out = sys.argv[2].upper(), sys.argv[3]
        d = iso_dir()
        if name not in d and (name + ';1') in d:      # ISO9660 版本后缀
            name = name + ';1'
        if name not in d:
            raise SystemExit('目录里没有 %s（可用：%s）'
                             % (name, [k for k in sorted(d) if ';' not in k or k.endswith(';1')][:6]))
        lba, sz, isd = d[name]
        idx, _t, _n = load_index()
        cnt = (sz + SEC - 1) // SEC
        data = read_sectors(idx, lba, cnt)
        if data is None:
            miss = [l for l in range(lba, lba + cnt) if l not in idx]
            raise SystemExit('%s: dump 缺 %d/%d 扇区（例 %s）'
                             % (name, len(miss), cnt, miss[:8]))
        open(out, 'wb').write(data[:sz])
        print('[out] %s  %d B（LBA %d..%d ; dump 覆盖 %d 扇区）'
              % (out, len(data[:sz]), lba, lba + cnt - 1, cnt))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
