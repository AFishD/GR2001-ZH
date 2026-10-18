# -*- coding: utf-8 -*-
r"""hk_lib.py — GR_HOOK (钩子二分打靶盘) 共享库。既有盘一律只读。

复用 GR_AB/ab_lib 的 ELF 解析与反汇编 (口径一致)。
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
for p in (os.path.join(REPO, 'work', 'builds', 'GR_AB', 'tools'),
          os.path.join(REPO, 'work', 'builds', 'GR_NULLHUNT', 'tools'),
          os.path.join(REPO, 'tools', 'gr_tools'), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import ab_lib as A          # noqa: E402
import nh_lib as N          # noqa: E402
import nh_elf as E          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_HOOK')
EVID = os.path.join(OUT, 'evidence')
BASE_ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
BASE_EN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')

ELF_ISO_BASE = 0x93800
ELF_LEN = 37453732
VA2FILE = 0xFFF80
VA2ISO = VA2FILE - ELF_ISO_BASE       # 0x6C780


def va2file(va):
    return va - VA2FILE


def va2iso(va):
    return va - VA2ISO


def iso2va(off):
    return off + VA2ISO


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


_ELF_CACHE = {}


def elf(tag):
    if tag not in _ELF_CACHE:
        if tag == 'EN':
            blob = open(BASE_EN, 'rb').read()  # 占位, 下面立即覆盖
            iso = N.Iso(BASE_EN)
            f = [v for k, v in iso.files().items() if 'SLUS_206.13' in k][0]
            blob = iso.rd(f['lba'] * N.SEC, f['size'])
            iso.close()
        else:
            with open(BASE_ZH, 'rb') as fh:
                fh.seek(ELF_ISO_BASE)
                blob = fh.read(ELF_LEN)
        _ELF_CACHE[tag] = E.Elf(blob, tag)
    return _ELF_CACHE[tag]


def base_elf_read(off, n):
    with open(BASE_ZH, 'rb') as fh:
        fh.seek(off)
        return fh.read(n)


def dis1(w, va):
    return A.dis1(w, va)


def dis(blob, va, count):
    return A.dis_range(blob, va, count, VA2FILE)


def sp_accesses(blob, va_start, va_end):
    """扫 sp-relative 的立即数内存访问 + addiu sp,sp,n / addiu rX,sp,n"""
    out = []
    for a in range(va_start, va_end, 4):
        o = a - VA2FILE
        if o < 0 or o + 4 > len(blob):
            continue
        w = struct.unpack_from('<I', blob, o)[0]
        op = w >> 26
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if rs == 29 and op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x1E, 0x37):
            out.append((a, 'R', A.dis1(w, a), 'sp%+d' % simm))
        elif rs == 29 and op in (0x28, 0x29, 0x2B, 0x1F, 0x3F, 0x2A, 0x2E):
            out.append((a, 'W', A.dis1(w, a), 'sp%+d' % simm))
        elif rs == 29 and op in (0x31, 0x39):
            out.append((a, 'R' if op == 0x31 else 'W', A.dis1(w, a), 'sp%+d' % simm))
        elif rs == 29 and op == 0x09:
            out.append((a, 'R', A.dis1(w, a), 'sp%+d' % simm))
    return out


def reg_writes(blob, va_start, va_end, reg):
    """找所有写 reg 的指令 (rt 或 rd == reg), 返回 [(va, dis)]"""
    out = []
    for a in range(va_start, va_end, 4):
        o = a - VA2FILE
        if o < 0 or o + 4 > len(blob):
            continue
        w = struct.unpack_from('<I', blob, o)[0]
        op = w >> 26
        rt = (w >> 16) & 0x1F
        rd = (w >> 11) & 0x1F
        hit = False
        if op == 0:                                   # SPECIAL: rd 目标
            funct = w & 0x3F
            if funct in (0x00, 0x02, 0x03, 0x04, 0x06, 0x07, 0x20, 0x21, 0x22, 0x23,
                         0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B, 0x08, 0x09, 0x10, 0x12,
                         0x2C, 0x2D, 0x2E, 0x2F, 0x3C, 0x3E, 0x3F):
                hit = (rd == reg)
        elif op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x20, 0x21, 0x23,
                    0x24, 0x25, 0x27, 0x1E, 0x37, 0x22, 0x26, 0x28, 0x29, 0x2B, 0x1F,
                    0x3F, 0x2A, 0x2E, 0x2C, 0x2D, 0x31, 0x35, 0x39, 0x3D, 0x30, 0x34,
                    0x38, 0x3C, 0x22, 0x26):
            hit = (rt == reg)
        if hit:
            out.append((a, A.dis1(w, a)))
    return out
