# -*- coding: utf-8 -*-
r"""de_capscan.py —— 顶点包容量/字体管理器结构偏移普查（只读）。

找出所有引用「立即数 1280/1279/1281」与「fontmgr 结构偏移 +0x28/+0x3C/+0x44/+0x48/
+0x4C/+0x60/+0x68/+0x6C/+0x70/+0x98/+0xF8/+0x108」的指令，用于定位顶点缓冲的分配点。

用法： python de_capscan.py <elf> [--off 0x28,0x44] [--imm 1280] [--ctx N]
"""
import importlib.util
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

DEF_OFF = {0x28: '+0x28', 0x44: '+0x44', 0x3C: '+0x3C', 0x48: '+0x48', 0x4C: '+0x4C',
           0x68: '+0x68', 0x60: '+0x60', 0x6C: '+0x6C', 0x70: '+0x70', 0x98: '+0x98',
           0xF8: '+0xF8', 0x108: '+0x108'}
DEF_IMM = {0x500: '1280', 0x4FF: '1279', 0x501: '1281', 0x400: '1024', 0x3FF: '1023'}
LOADST = {0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x37, 0x28, 0x29, 0x2A, 0x2B, 0x3F, 0x1E, 0x1F}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elf = CD.Elf(sys.argv[1])
    offs = dict(DEF_OFF)
    imms = dict(DEF_IMM)
    ctx = 0
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--off':
            offs = {}
            for x in sys.argv[i + 1].split(','):
                v = int(x, 16) if x.startswith('0x') else int(x)
                offs[v] = hex(v)
            i += 2
        elif sys.argv[i] == '--imm':
            imms = {}
            for x in sys.argv[i + 1].split(','):
                v = int(x, 16) if x.startswith('0x') else int(x)
                imms[v] = str(v)
            i += 2
        elif sys.argv[i] == '--ctx':
            ctx = int(sys.argv[i + 1]); i += 2
        else:
            i += 1
    va0, off0, fsz = elf.text()
    hi = va0 + fsz
    hits = []
    for va in range(va0, hi - 4, 4):
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        rs, rt = (w >> 21) & 0x1F, (w >> 16) & 0x1F
        imm = w & 0xFFFF
        simm = struct.unpack('<h', struct.pack('<H', imm))[0]
        if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F) and imm in imms:
            hits.append((va, w, 'IMM %s (rt=%s)' % (imms[imm], CD.GPR[rt])))
        if op in LOADST and simm in offs:
            hits.append((va, w, 'MEM off %s base=$%s rt=$%s' % (offs[simm], CD.GPR[rs], CD.GPR[rt])))
    print('# %s' % sys.argv[1])
    print('# 命中 %d 条' % len(hits))
    for (va, w, s) in hits:
        print('  0x%08X  %08X  %-30s %s' % (va, w, s, CD.dis(w, va)))
        if ctx:
            for k in range(1, ctx + 1):
                w2 = elf.word(va + 4 * k)
                print('        +0x%02X  0x%08X  %s' % (4 * k, w2, CD.dis(w2, va + 4 * k)))


if __name__ == '__main__':
    main()
