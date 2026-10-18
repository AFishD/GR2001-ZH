# -*- coding: utf-8 -*-
r"""de_fontmgr.py —— 定位「字体管理器对象」的构造点：谁给 +0x28 / +0x4C 装顶点包对象，
谁写 +0x44 / +0x68（顶点计数），以及顶点包缓冲的容量从哪来。

只读。
用法： python de_fontmgr.py <elf>
"""
import importlib.util
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

SP = 29
# 目标：addiu/sp-relative 排除；只看「对象基址」上的这些偏移
WANT = {0x28: 'primary packet obj', 0x4C: 'secondary packet obj', 0x44: 'primary count',
        0x68: 'secondary count', 0x3C: 'primary last', 0x60: 'secondary last',
        0x48: 'flush-flag', 0x70: 'fontmgr+0x70 (float)', 0x98: 'font obj ptr'}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    va0, off0, fsz = elf.text()
    hi = va0 + fsz
    print('# %s' % sys.argv[1])
    for off in sorted(WANT):
        rows = []
        for va in range(va0, hi - 4, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            rs, rt = (w >> 21) & 0x1F, (w >> 16) & 0x1F
            imm = w & 0xFFFF
            if op not in (0x28, 0x29, 0x2A, 0x2B, 0x20, 0x21, 0x23, 0x24, 0x25, 0x37, 0x3F):
                continue
            if imm != off or rs == SP:
                continue
            # 只保留"写"（store）
            if op in (0x28, 0x29, 0x2A, 0x2B, 0x3F):
                rows.append((va, w, CD.dis(w, va)))
        if rows:
            print()
            print('## 偏移 +0x%02X (%s)：写点 %d 个' % (off, WANT[off], len(rows)))
            for (va, w, s) in rows:
                print('    0x%08X  %08X  %s' % (va, w, s))


if __name__ == '__main__':
    main()
