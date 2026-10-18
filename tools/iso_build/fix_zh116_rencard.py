# -*- coding: utf-8 -*-
r"""fix_zh116_rencard.py — 在记忆卡副本上**改名**指定前缀的目录项 (保持目录结构完全合法)

为什么不用"清 mode 位": 实测那样会让 PCSX2 把整张卡当成不可用 ⇒ 游戏报"没有记忆卡",
对照实验失效。改名(等长)则卡片结构不变, 但游戏按名字匹配就找不到自己的存档。

用法: python tools/iso_build/fix_zh116_rencard.py <src.ps2> <dst.ps2> --from BASLUS-20613 --to BASLUS-20613X
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
    ap.add_argument('--from', dest='frm', required=True)
    ap.add_argument('--to', dest='to', required=True)
    a = ap.parse_args()
    assert len(a.frm) == len(a.to), '必须等长改名'
    shutil.copy2(a.src, a.dst)
    npages = os.path.getsize(a.dst) // PAGE_RAW
    n = 0
    with open(a.dst, 'r+b') as f:
        for pg in range(npages):
            f.seek(pg * PAGE_RAW + 0x40)
            nm = f.read(32).split(b'\x00')[0]
            if nm.startswith(a.frm.encode()):
                new = a.to.encode() + nm[len(a.frm):]
                f.seek(pg * PAGE_RAW + 0x40)
                f.write(new + b'\x00' * (32 - len(new)))
                n += 1
                print('   pg%-6d %s -> %s' % (pg, nm.decode(), new.decode()))
    print('改名 %d 处 -> %s' % (n, a.dst))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
