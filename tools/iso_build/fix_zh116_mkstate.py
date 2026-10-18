# -*- coding: utf-8 -*-
r"""fix_zh116_mkstate.py — 改写即时存档 (只改 eeMemory.bin 里指定的字节) → 新 .p2s

用途 (r70): 把存档里 **汉化 ELF 与英文原盘 ELF 不同的那些字节** 还原成英文值,
得到"游戏状态不变、但 RAM 里的补丁被撤掉"的对照存档 ⇒ 判断卡死是否由汉化补丁引起。

用法:
  python tools/iso_build/fix_zh116_mkstate.py <src.p2s> <dst.p2s> --revert-elf <en.iso> [--zh <zh.iso>]
"""
import argparse
import os
import struct
import sys
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import fix_zh116_p2s as P  # noqa: E402
import tcslib  # noqa: E402

ELF_LBA = 295
ELF_SIZE = 37453732
SEG_OFF = 0x80
SEG_VA = 0x100000
SEG_FILESZ = 5106944


def elf_of(iso):
    f = tcslib.Iso(iso)
    try:
        return f.read(ELF_LBA * 2048, ELF_SIZE)
    finally:
        f.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--revert-elf', required=True, help='英文原盘 ISO (补丁字节的来源)')
    ap.add_argument('--zh', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso'))
    ap.add_argument('--report', default=None)
    a = ap.parse_args()

    en = elf_of(a.revert_elf)
    zh = elf_of(a.zh)
    ram = bytearray(P.read_entry(a.src, 'eeMemory.bin'))
    print('state eeMemory.bin = %d B' % len(ram))

    diffs = []
    for i in range(SEG_FILESZ):
        z = zh[SEG_OFF + i]
        e = en[SEG_OFF + i]
        if z != e:
            va = SEG_VA + i
            diffs.append((va, z, e))
    print('汉化 ELF vs 英文 ELF 差异字节: %d' % len(diffs))
    for va, z, e in diffs:
        ram[va] = e
    print('已把 %d 个字节还原为英文值' % len(diffs))
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            for va, z, e in diffs:
                f.write('%08X %02X->%02X\n' % (va, z, e))
        print('差异清单 -> %s' % a.report)

    # 重写 zip: 版本指示文件保持 stored, 其余 deflate
    with zipfile.ZipFile(a.src) as z:
        infos = z.infolist()
    with zipfile.ZipFile(a.dst, 'w', zipfile.ZIP_DEFLATED) as out:
        for info in infos:
            data = bytes(ram) if info.filename == 'eeMemory.bin' else P.read_entry(a.src, info.filename)
            if info.filename == 'PCSX2 Savestate Version.id':
                zi = zipfile.ZipInfo(info.filename)
                out.writestr(zi, data, compress_type=zipfile.ZIP_STORED)
            else:
                out.writestr(info.filename, data, compress_type=zipfile.ZIP_DEFLATED)
    print('写出 %s (%d B)' % (a.dst, os.path.getsize(a.dst)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
