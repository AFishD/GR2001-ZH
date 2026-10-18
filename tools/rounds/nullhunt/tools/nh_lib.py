# -*- coding: utf-8 -*-
r"""nh_lib.py — GR_NULLHUNT 只读共享库 (NULL 解引用根因审计)

只读: 全部 ISO 以 mmap ACCESS_READ 打开, 不写任何既有文件。
本文件只被 GR_NULLHUNT 下的脚本引用。
"""
import mmap
import os
import struct

SEC = 2048
# 本文件位于 <REPO>\work\builds\GR_NULLHUNT\tools\nh_lib.py ⇒ 上溯 4 级 = REPO
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))

ISO = {
    'ZH113b':     os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'),
    'ZH113b_fix': os.path.join(REPO, 'work', 'builds', 'GR_ZH113b_fix', 'GR_ZH113b_fix.iso'),
    'EN_ORIG':    os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'),
}
OUT = os.path.join(REPO, 'work', 'builds', 'GR_NULLHUNT')
EVID = os.path.join(OUT, 'evidence')

# IMG 容器条目表: 表头 = IMG_BASE + TAB_OFF, 每项 48 B = 12 x u32
TAB_OFF, TAB_STEP = 0x830, 48
# 字段语义 (自证见 nh_stage1 报告; 与 zx_lib.py / iso_tools.py 一致):
#   u32[0] = 名字偏移 (相对 IMG 起点)
#   u32[6] = stored  (盘上字节数)
#   u32[7] = real    (解压后字节数; 引擎读流上界 = min(stored, real))
#   u32[8] = off     (相对 IMG 起点的数据偏移)


class Iso:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        self.sectors = (self.size + SEC - 1) // SEC

    def rd(self, off, n):
        return bytes(self.mm[off:off + n])

    def u32(self, off):
        return struct.unpack_from('<I', self.mm, off)[0]

    def close(self):
        self.mm.close()
        self.f.close()

    # ---------------------------------------------------------------- ISO9660
    def pvd(self):
        p = 16 * SEC
        assert bytes(self.mm[p + 1:p + 6]) == b'CD001', 'not ISO9660: %s' % self.path
        return dict(vol_size=self.u32(p + 80), vol_size_be=struct.unpack_from('>I', self.mm, p + 84)[0],
                    root_lba=self.u32(p + 158), root_size=self.u32(p + 166),
                    path_lba=self.u32(p + 140), path_size=self.u32(p + 132))

    def dirrecs(self, lba, size):
        """→ [(name, ext, sz, flags, rec_off, rec_len)]
        同时抓出每条记录的**双端序重复字段**是否自洽。"""
        out = []
        start = lba * SEC
        data = bytes(self.mm[start:start + size])
        i = 0
        while i < len(data):
            L = data[i]
            if L == 0:
                i = (i // SEC + 1) * SEC
                if i >= len(data):
                    break
                continue
            if i + L > len(data) or L < 34:
                out.append(('!!MALFORMED', i, L, None, start + i, L))
                break
            rec = data[i:i + L]
            ext_le = struct.unpack_from('<I', rec, 2)[0]
            ext_be = struct.unpack_from('>I', rec, 6)[0]
            sz_le = struct.unpack_from('<I', rec, 10)[0]
            sz_be = struct.unpack_from('>I', rec, 14)[0]
            nlen = rec[32]
            nm = rec[33:33 + nlen]
            flags = rec[25]
            ok = (ext_le == ext_be) and (sz_le == sz_be)
            out.append((nm.decode('latin-1'), ext_le, sz_le, flags, start + i, L,
                        ok, ext_be, sz_be))
            i += L
        return out

    def files(self):
        """→ {path: dict(lba,size,flags,rec_off,dual_ok)} 递归 (本盘只有根目录 + 1 子目录)"""
        out = {}

        def walk(lba, size, prefix, depth=0):
            for r in self.dirrecs(lba, size):
                nm = r[0]
                if nm in ('\x00', '\x01') or nm.startswith('!!'):
                    continue
                p = prefix + '/' + nm
                out[p] = dict(lba=r[1], size=r[2], flags=r[3], rec_off=r[4],
                              rec_len=r[5], dual_ok=r[6], ext_be=r[7], sz_be=r[8])
                if (r[3] & 2) and depth < 4:
                    walk(r[1], r[2], p, depth + 1)
        pv = self.pvd()
        walk(pv['root_lba'], pv['root_size'], '')
        return out

    # ------------------------------------------------------------------- IMG
    def img_header(self, lba):
        base = lba * SEC
        h = list(struct.unpack_from('<12I', self.mm, base))
        return dict(base=base, raw=h, size=h[0], names_end=h[1], sector=h[2],
                    tbl_end=h[3], names_start=h[4], data_start=h[5],
                    h8=h[8], h9=h[9], h10=h[10], h11=h[11])

    def img_names(self, lba, hdr=None):
        h = hdr or self.img_header(lba)
        base = h['base']
        blob = bytes(self.mm[base + h['names_start']:base + h['names_end']])
        return [x.decode('latin-1') for x in blob.split(b'\x00') if x]

    def img_entries(self, lba, n=None):
        """按名字表条目数解析全部 48 B 条目。返回 [dict]"""
        h = self.img_header(lba)
        base = h['base']
        names = self.img_names(lba, h)
        cnt = len(names) if n is None else n
        out = []
        for i in range(cnt):
            r = list(struct.unpack_from('<12I', self.mm, base + TAB_OFF + TAB_STEP * i))
            out.append(dict(idx=i, name=names[i] if i < len(names) else '?', raw=r,
                            nameoff=r[0], stored=r[6], real=r[7], off=r[8],
                            f1=r[1], f2=r[2], f3=r[3], f4=r[4], f5=r[5],
                            f9=r[9], f10=r[10], f11=r[11],
                            iso_off=base + r[8]))
        return out, h, names


def fmt(n):
    return '{:,}'.format(n)
