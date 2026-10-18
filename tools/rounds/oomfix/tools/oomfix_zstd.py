# -*- coding: utf-8 -*-
r"""oomfix_zstd.py —— 只用一个 zip + zstd.dll 读写 PCSX2 .p2s（ZIP, 方法 93 = zstd）。

背景（本轮实测）：PCSX2 的即时存档把 **EE 32 MB 主存整体**存进 `eeMemory.bin`；
`-grstate` 载入后 VM 直接从存档的 PC 继续跑，**BIOS 不会再从光盘装载 ELF**，
所以「只改 ISO」的补丁在载入存档后会被存档里的旧代码覆盖。
⇒ 要在**同一现场**验证代码修复，必须把补丁同时打进存档的 `eeMemory.bin`。

本工具用 ctypes 调 PCSX2 自带的 `zstd.dll`，不依赖 Python 的 zstd 支持。
READ-ONLY 打开输入；只写 --out。

用法:
  python oomfix_zstd.py list   <in.p2s>
  python oomfix_zstd.py read   <in.p2s> <entry> <out.bin>
  python oomfix_zstd.py patch  <in.p2s> <out.p2s> --entry eeMemory.bin --apply <spec.json>
      <spec.json> = [{"va": "0x539174", "old": "AE620004", "new": "08154012"}, ...]
      （old 不符即中止；--force 可跳过）
  python oomfix_zstd.py verify <in.p2s> <entry> --apply <spec.json>
"""
import argparse
import ctypes
import hashlib
import json
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
ZSTD_DLL = os.path.join(ROOT, 'work', 'builds', 'GR_OOMFIX', 'emu', 'gsrunner', 'zstd.dll')


def zstd():
    lib = ctypes.CDLL(ZSTD_DLL)
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                    ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_compress.restype = ctypes.c_size_t
    lib.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    lib.ZSTD_isError.restype = ctypes.c_uint
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    return lib


def zip_entries(path):
    """返回 [(name, method, comp_size, uncomp_size, header_offset)]（读中央目录）。"""
    z = zipfile.ZipFile(path)
    out = []
    for i in z.infolist():
        out.append(dict(name=i.filename, method=i.compress_type,
                        csize=i.compress_size, usize=i.file_size,
                        hdr=i.header_offset, crc=i.CRC))
    z.close()
    return out


def read_raw(path, ent):
    """从本地文件头读出一个条目的**压缩**原始字节（长度以中央目录为准）。"""
    with open(path, 'rb') as f:
        f.seek(ent['hdr'])
        sig, ver, flag, method, mtime, mdate, crc, csize, usize, nlen, elen = \
            struct.unpack('<IHHHHHIIIHH', f.read(30))
        assert sig == 0x04034B50, hex(sig)
        ent['flag'] = flag
        ent['local_csize'] = csize
        ent['local_usize'] = usize
        name = f.read(nlen)
        f.read(elen)
        data = f.read(ent['csize'])
    return data, name.decode('latin-1')


def decompress_entry(path, entry_name):
    lib = zstd()
    for e in zip_entries(path):
        if e['name'] != entry_name:
            continue
        raw, _n = read_raw(path, e)
        if e['method'] == 0:
            return raw
        if e['method'] != 93:
            raise SystemExit('不支持的压缩方法 %d' % e['method'])
        out = ctypes.create_string_buffer(e['usize'])
        n = lib.ZSTD_decompress(out, e['usize'], raw, len(raw))
        if lib.ZSTD_isError(n):
            raise SystemExit('ZSTD_decompress 失败 (%d)' % n)
        assert n == e['usize'], (n, e['usize'])
        return out.raw[:e['usize']]
    raise SystemExit('条目不存在: %s' % entry_name)


def compress_zstd(data, level=3):
    lib = zstd()
    cap = len(data) + (len(data) >> 8) + 1024
    out = ctypes.create_string_buffer(cap)
    n = lib.ZSTD_compress(out, cap, data, len(data), level)
    if lib.ZSTD_isError(n):
        raise SystemExit('ZSTD_compress 失败 (%d)' % n)
    return out.raw[:n]


def rewrite(path_in, path_out, entry_name, new_data):
    """把 entry_name 换成 new_data（zstd），其余条目**逐字节原样搬运**。"""
    ents = zip_entries(path_in)
    payloads = {}
    for e in ents:
        raw, _nm = read_raw(path_in, e)
        payloads[e['name']] = raw
        if e['name'] == entry_name:
            payloads[e['name']] = compress_zstd(new_data)
    meta = {}
    for e in ents:
        meta[e['name']] = dict(method=e['method'], csize=len(payloads[e['name']]),
                               usize=len(new_data) if e['name'] == entry_name else e['usize'],
                               crc=(zipfile.crc32(new_data) & 0xFFFFFFFF)
                               if e['name'] == entry_name else e['crc'])
    tmp = path_out + '.tmp'
    with open(tmp, 'wb') as fo:
        offsets = {}
        for e in ents:
            m = meta[e['name']]
            offsets[e['name']] = fo.tell()
            fo.write(struct.pack('<IHHHHHIIIHH', 0x04034B50, 20, 0, m['method'],
                                 0, 0, m['crc'], m['csize'], m['usize'], len(e['name']), 0))
            fo.write(e['name'].encode('latin-1'))
            fo.write(payloads[e['name']])
        cd_off = fo.tell()
        for e in ents:
            m = meta[e['name']]
            fo.write(struct.pack('<IHHHHHHIIIHHHHHII', 0x02014B50, 20, 20, 0, m['method'],
                                 0, 0, m['crc'], m['csize'], m['usize'],
                                 len(e['name']), 0, 0, 0, 0, 0, offsets[e['name']]))
            fo.write(e['name'].encode('latin-1'))
        cd_size = fo.tell() - cd_off
        fo.write(struct.pack('<IHHHHIIH', 0x06054B50, 0, 0, len(ents), len(ents),
                             cd_size, cd_off, 0))
    os.replace(tmp, path_out)
    # 自证：逐条目回读并比对
    bad = []
    for e in ents:
        got = decompress_entry(path_out, e['name'])
        ref = new_data if e['name'] == entry_name else decompress_entry(path_in, e['name'])
        if got != ref:
            bad.append(e['name'])
    if bad:
        raise SystemExit('[FAIL] 重写后回读不符的条目: %s' % bad)
    print('   [自证] %d 个条目重写后逐字节回读一致' % len(ents))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['list', 'read', 'patch', 'verify'])
    ap.add_argument('p2s')
    ap.add_argument('a', nargs='?')
    ap.add_argument('b', nargs='?')
    ap.add_argument('--entry', default='eeMemory.bin')
    ap.add_argument('--apply', default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    if a.mode == 'list':
        for e in zip_entries(a.p2s):
            print('  %-30s method=%2d usize=%-10d csize=%-10d' % (e['name'], e['method'],
                                                                  e['usize'], e['csize']))
        return 0
    if a.mode == 'read':
        data = decompress_entry(a.p2s, a.entry)
        open(a.a, 'wb').write(data)
        print('%s:%s -> %s  %d B sha256=%s' % (a.p2s, a.entry, a.a, len(data),
                                               hashlib.sha256(data).hexdigest()))
        return 0
    if a.mode == 'verify':
        data = decompress_entry(a.p2s, a.entry)
        spec = json.load(open(a.apply, encoding='utf-8'))
        for s in spec:
            va = int(s['va'], 16)
            got = struct.unpack_from('<I', data, va)[0]
            print('   0x%08X = %08X (期望 %s) %s' % (va, got, s['new'].upper(),
                                                     'OK' if got == int(s['new'], 16) else 'FAIL'))
        return 0

    data = bytearray(decompress_entry(a.p2s, a.entry))
    spec = json.load(open(a.apply, encoding='utf-8'))
    for s in spec:
        va = int(s['va'], 16)
        old, new = int(s['old'], 16), int(s['new'], 16)
        got = struct.unpack_from('<I', data, va)[0]
        if got != old and not a.force:
            raise SystemExit('0x%08X 原字不符：%08X ≠ %08X' % (va, got, old))
        struct.pack_into('<I', data, va, new)
        print('   0x%08X  %08X -> %08X  %s' % (va, got, new, s.get('note', '')))
    rewrite(a.p2s, a.a, a.entry, bytes(data))
    # 回读
    chk = decompress_entry(a.a, a.entry)
    ok = all(struct.unpack_from('<I', chk, int(s['va'], 16))[0] == int(s['new'], 16) for s in spec)
    assert ok, '回读不符'
    print('[out] %s  %d B  sha256=%s（回读 OK）'
          % (a.a, os.path.getsize(a.a), hashlib.sha256(open(a.a, 'rb').read()).hexdigest()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
