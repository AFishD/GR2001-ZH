# -*- coding: utf-8 -*-
r"""hg_lib.py — GR_HUGE (huge 面 nrec 恢复打靶盘) 共享库。**只读**既有盘。

复用 GR_AB 的 ab_lib (只读 mmap) 与 tools/gr_tools 的 LZO 编解码。
只读对象: work/builds/GR_ZH113b/GR_ZH113b.iso, work/builds/GR_EN_ORIG/GR_EN_ORIG.iso,
          third_party/orig/ps2/*.iso
写入范围: work/builds/GR_HUGE/**  (本文件永不写既有盘)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
AB_TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_AB', 'tools')
for p in (AB_TOOLS, os.path.join(REPO, 'tools', 'gr_tools')):
    if p not in sys.path:
        sys.path.insert(0, p)

import ab_lib as A      # noqa: E402
import nh_lib as N      # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_HUGE')
EVID = os.path.join(OUT, 'evidence')
SEC = N.SEC
BASE_ZH = A.BASE_ZH
BASE_EN = A.BASE_EN
ISO = A.ISO
IMG = A.IMG
VA2ISO = A.VA2ISO
VA2FILE = A.VA2FILE
ELF_LBA = A.ELF_LBA
ELF_ISO_BASE = A.ELF_ISO_BASE
dis1 = A.dis1
dis_range = A.dis_range

# FONT.RES 展开态布局 (docs/FONTRES_STRUCTURE_r83.md §2.6)
HEAD_LEN = 24           # [u32 20][20 B "new_font_revised.rsb"]  → 4+20 = 24
NFACES_OFF = 24
FACE_HDR = 56           # 14 × u32
REC_LEN = 10            # <BB4H>
EN_HUGE_FLD45 = (16, 14)   # 英文原盘 huge 面 fld[4]×fld[5] = 224


def parse_faces(plain):
    """展开态明文 → (faces, styles_off)
    faces = [dict(name, nr, fld_off, fld, rec_off, recs(bytes))]
    """
    p = 0
    l0 = int.from_bytes(plain[0:4], 'little')
    p = 4 + l0                                     # 4 + 20 = 24
    n = int.from_bytes(plain[p:p + 4], 'little')
    p += 4
    faces = []
    for _ in range(n):
        l = int.from_bytes(plain[p:p + 4], 'little')
        p += 4
        nm = plain[p:p + l].decode('latin-1')
        p += l
        fld_off = p
        fld = list(int.from_bytes(plain[p + 4 * i:p + 4 * i + 4], 'little') for i in range(14))
        p += FACE_HDR
        nr = fld[4] * fld[5]
        rec_off = p
        recs = bytes(plain[p:p + nr * REC_LEN])
        p += nr * REC_LEN
        faces.append(dict(name=nm.rstrip('\x00'), nr=nr, fld_off=fld_off, fld=fld,
                          rec_off=rec_off, recs=recs))
    return faces, p, n


def rec_at(face, idx):
    """→ (b0,b1,u0,v0,u1,v1)"""
    import struct
    o = idx * REC_LEN
    return struct.unpack_from('<BB4H', face['recs'], o)


def fontres(tag, imgk):
    """→ dict(entry, base, raw, plain, comp, real, faces, styles_off, nfaces)"""
    iso = N.Iso(ISO[tag])
    e, base, raw, ents = A.fontres_entry(iso, IMG[imgk])
    iso.close()
    plain, comp, real, se = A.decompress_fontres(raw)
    faces, styles_off, nf = parse_faces(plain)
    return dict(entry=e, base=base, raw=raw, plain=plain, comp=comp, real=real,
                faces=faces, styles_off=styles_off, nfaces=nf)


def sha256_file(path, chunk=1 << 22):
    return A.sha256_file(path, chunk)


# --------------------------------------------------- 独立第二解码器 (自检用)
ALT_DEC_PATH = os.path.join(REPO, 'tools', 'hanliu', 'tools', 'lz77_decode.py')


def alt_decompress(stream, out_size):
    """用 tools/hanliu/tools/lz77_decode.py（与 tools/gr_tools 版本**不同文件、不同实现**）
    独立解压一次，返回 bytes。用于"两个独立解码器互证"。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('hg_alt_lz77', ALT_DEC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.lzo1x_decompress(stream, out_size)
    if isinstance(r, tuple):
        r = r[0]
    return bytes(r)
