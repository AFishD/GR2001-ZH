# -*- coding: utf-8 -*-
r"""p2s.py -- read members out of a PCSX2 .p2s savestate, including members
compressed with Zstandard (zip compress_type 93), which CPython's zipfile does
not support before 3.14.  Uses the zstd DLL shipped with the emulator build.

READ-ONLY on the savestate; nothing is modified.

usage (module):   from p2s import read_member, ee_ram
usage (cli):      python p2s.py list  <state.p2s|.backup>
                  python p2s.py ee    <state.p2s|.backup> <out.bin>
                  python p2s.py words <state.p2s|.backup> <addr_hex> <count>
"""
import ctypes
import os
import struct
import sys
import zipfile

ZSTD_CANDIDATES = [
    r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_CULPRIT\emu\gsrunner\zstd.dll',
    r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\third_party\emu\pcsx2\pcsx2-gsrunner\zstd.dll',
]
_Z = None


def _zstd():
    global _Z
    if _Z is None:
        path = next((p for p in ZSTD_CANDIDATES if os.path.exists(p)), None)
        if path is None:
            raise SystemExit('zstd.dll not found')
        lib = ctypes.CDLL(path)
        lib.ZSTD_decompress.restype = ctypes.c_size_t
        lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.c_void_p, ctypes.c_size_t]
        lib.ZSTD_isError.restype = ctypes.c_uint
        lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        lib.ZSTD_getErrorName.restype = ctypes.c_char_p
        lib.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]
        _Z = lib
    return _Z


def _raw_member(path, name):
    """return (compress_type, uncompressed_size, raw_bytes_of_member)"""
    with zipfile.ZipFile(path) as z:
        info = None
        for i in z.infolist():
            if i.filename == name:
                info = i
                break
        if info is None:
            raise KeyError('%s not in %s' % (name, path))
        with open(path, 'rb') as f:
            f.seek(info.header_offset)
            hdr = f.read(30)
            if hdr[:4] != b'PK\x03\x04':
                raise SystemExit('bad local header at 0x%X' % info.header_offset)
            nlen, elen = struct.unpack_from('<HH', hdr, 26)
            f.seek(info.header_offset + 30 + nlen + elen)
            raw = f.read(info.compress_size)
    return info.compress_type, info.file_size, raw


def list_members(path):
    with zipfile.ZipFile(path) as z:
        return [(i.filename, i.compress_type, i.file_size, i.compress_size)
                for i in z.infolist()]


def read_member(path, name):
    ctype, usize, raw = _raw_member(path, name)
    if ctype == 0:
        return raw
    if ctype == 8:
        import zlib
        return zlib.decompress(raw, -15)
    if ctype == 93:
        lib = _zstd()
        dst = ctypes.create_string_buffer(usize)
        src = ctypes.create_string_buffer(raw, len(raw))
        got = lib.ZSTD_decompress(dst, ctypes.c_size_t(usize), src, ctypes.c_size_t(len(raw)))
        if lib.ZSTD_isError(got):
            raise SystemExit('zstd: %s' % lib.ZSTD_getErrorName(got).decode())
        return dst.raw[:got]
    raise SystemExit('unsupported zip method %d' % ctype)


def ee_ram(path):
    return read_member(path, 'eeMemory.bin')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode, path = sys.argv[1], sys.argv[2]
    if mode == 'list':
        for m in list_members(path):
            print('   %-40s method=%-3d usize=%10d csize=%10d' % m)
        return
    if mode == 'ee':
        d = ee_ram(path)
        open(sys.argv[3], 'wb').write(d)
        print('wrote %d bytes -> %s' % (len(d), sys.argv[3]))
        return
    if mode == 'words':
        d = ee_ram(path)
        a = int(sys.argv[3], 16)
        n = int(sys.argv[4], 0)
        for i in range(n):
            print('  %08X  %08X' % (a + 4 * i, struct.unpack_from('<I', d, a + 4 * i)[0]))
        return
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
