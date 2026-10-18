# -*- coding: utf-8 -*-
r"""sf_common.py —— 【GR_SPINFIX】共享工具：ISO/ELF 读取、sha256、diff_runs、p2s 存取。

READ-ONLY：本模块只以 'rb' 打开输入文件；写入由调用方负责。
p2s 的 zip+zstd 逻辑**直接复用** GR_OOMFIX 已验证的 oomfix_zstd.py（不重写、不改动）。
"""
import hashlib
import importlib.util
import os
import struct
import sys

SEC = 2048
ELF_NAME = 'SLUS_206.13'
ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'

# 地址换算（由 PT_LOAD va=0x00100000 off=0x80、ELF @LBA 295 推出；本模块会自行断言）
ELF_LBA = 295
ISO_OF_VA = 0x6C780          # ISO 偏移 = VA − 0x6C780
ELF_OF_VA = 0xFFF80          # ELF 文件偏移 = VA − 0xFFF80（= VA − 0x100000 + 0x80）


def sha256_file(p, blk=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(blk), b''):
            h.update(b)
    return h.hexdigest()


def iso_find_elf(f):
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    assert pvd[1:6] == b'CD001', '扇区 16 不是 ISO9660 PVD'
    root = pvd[156:156 + 34]
    rlba = struct.unpack_from('<I', root, 2)[0]
    rsize = struct.unpack_from('<I', root, 10)[0]
    data = b''
    for i in range((rsize + SEC - 1) // SEC):
        f.seek((rlba + i) * SEC)
        data += f.read(SEC)
    off = 0
    while off < len(data):
        ln = data[off]
        if ln == 0:
            off = (off // SEC + 1) * SEC
            continue
        rec = data[off:off + ln]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode('latin-1').upper()
        if name in (ELF_NAME + ';1', ELF_NAME):
            return ext, sz
        off += ln
    raise SystemExit('ISO 目录里找不到 %s' % ELF_NAME)


def read_elf_from_iso(path):
    """返回 (elf_bytes, lba, size)。READ-ONLY。"""
    with open(path, 'rb') as f:
        lba, size = iso_find_elf(f)
        f.seek(lba * SEC)
        d = f.read(size)
    assert d[:4] == b'\x7fELF', 'ELF 魔数不对'
    return d, lba, size


def elf_off(va, lba=ELF_LBA):
    """VA -> ELF 文件内偏移。"""
    return va - ISO_OF_VA - lba * SEC


def word_at(elf, va, lba=ELF_LBA):
    return struct.unpack_from('<I', elf, elf_off(va, lba))[0]


def diff_runs(a, b, blk=1 << 22):
    """逐字节比较两个文件，返回 [(off, old_bytes, new_bytes), ...]（连续段）。"""
    runs, cur, off = [], None, 0
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            ba, bb = fa.read(blk), fb.read(blk)
            if not ba and not bb:
                break
            if len(ba) != len(bb):
                raise SystemExit('尺寸不同')
            if ba != bb:
                for i in range(len(ba)):
                    if ba[i] != bb[i]:
                        if cur is None:
                            cur = [off + i, bytearray(), bytearray()]
                        cur[1].append(ba[i])
                        cur[2].append(bb[i])
                    elif cur is not None:
                        runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
                        cur = None
            elif cur is not None:
                runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
                cur = None
            off += len(ba)
    if cur is not None:
        runs.append((cur[0], bytes(cur[1]), bytes(cur[2])))
    return runs


def load_zstd_tool():
    """导入 GR_OOMFIX 的 oomfix_zstd（只读导入，不执行 main）。"""
    p = os.path.join(ROOT, 'work', 'builds', 'GR_OOMFIX', 'tools', 'oomfix_zstd.py')
    spec = importlib.util.spec_from_file_location('oomfix_zstd', p)
    m = importlib.util.module_from_spec(spec)
    sys.modules['oomfix_zstd'] = m
    spec.loader.exec_module(m)
    return m


# ── 反汇编（复用 GR_CULPRIT 的 dis2.py：独立实现、无 rd 丢失 bug）─────────────
def load_dis2():
    p = os.path.join(ROOT, 'work', 'builds', 'GR_CULPRIT', 'tools', 'dis2.py')
    spec = importlib.util.spec_from_file_location('dis2', p)
    m = importlib.util.module_from_spec(spec)
    sys.modules['dis2'] = m
    spec.loader.exec_module(m)
    return m


def dis_list(words, va0):
    """把 [(va, word)] 反汇编成字符串列表。"""
    d = load_dis2()
    return ['  0x%08X  %08X  %s' % (va, w, d.dis(w, va)) for (va, w) in
            [(va0 + 4 * i, w) for i, w in enumerate(words)]]
