# -*- coding: utf-8 -*-
r"""fix_zh116_mkcard.py — 在**记忆卡副本**上删除指定前缀的目录项 (只读原卡, 写副本)

用途: 造"有卡但没有某游戏存档"的对照卡 (PCSX2 判 IsUsed = mode & 0x8000 ⇒ 清掉该位即视为空)。
记录头 512B 在每页 512B 数据区开头 (页原始步长 528B, 前 16B ECC 在数据之后)。

用法:
  python tools/iso_build/fix_zh116_mkcard.py <src.ps2> <dst.ps2> --drop BASLUS-20613
"""
import argparse
import os
import shutil
import sys

PAGE_RAW = 528


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--drop', required=True)
    a = ap.parse_args()
    shutil.copy2(a.src, a.dst)
    size = os.path.getsize(a.dst)
    npages = size // PAGE_RAW
    dropped = []
    with open(a.dst, 'r+b') as f:
        for pg in range(npages):
            f.seek(pg * PAGE_RAW)
            e = f.read(512)
            if len(e) < 512:
                break
            mode = int.from_bytes(e[0:4], 'little')
            if mode in (0, 0xFFFFFFFF) or not (mode & 0x8000):
                continue
            name = e[0x40:0x60].split(b'\x00')[0].decode('ascii', 'replace')
            if name.startswith(a.drop):
                f.seek(pg * PAGE_RAW)
                f.write((mode & ~0x8000).to_bytes(4, 'little'))
                dropped.append((pg, name, '%08X' % mode))
    print('删掉 %d 个目录项:' % len(dropped))
    for pg, nm, md in dropped:
        print('   pg%-6d %-24s mode=%s' % (pg, nm, md))
    print('-> %s' % a.dst)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
