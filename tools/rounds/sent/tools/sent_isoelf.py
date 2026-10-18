# -*- coding: utf-8 -*-
r"""sent_isoelf.py —— 从 ISO 里就地读 ELF（ISO = VA − 0x6C780，只读）。

用法：
  python sent_isoelf.py <iso> hdr                     # ELF 头 + PT_LOAD
  python sent_isoelf.py <iso> word <VA> [<VA> ...]    # 逐 VA 打印字 + 反汇编
  python sent_isoelf.py <iso> dis <loVA> <hiVA>       # 线性反汇编（带原始字节）
"""
import os
import struct
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

ISO_OF_VA = 0x6C780
ELF_VA0 = 0x100000


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    iso = sys.argv[1]
    mode = sys.argv[2]
    f = open(iso, 'rb')

    def rd(off, n):
        f.seek(off)
        return f.read(n)

    # 定位 ISO 里的 ELF 头：VA − ISO = 0x6C780 是**代码区**口径，
    # ELF 头在它前面 0x80（= 第一个 PT_LOAD 的 off）。向前扫魔法自证。
    hint = ELF_VA0 - ISO_OF_VA
    base = None
    for off in range(hint, hint - 0x400, -1):
        if rd(off, 4) == b'\x7fELF':
            base = off
            break
    if base is None:
        raise SystemExit('在 ISO 0x%X 往前 0x400 内没找到 ELF 魔法' % hint)

    # ★ VA→ISO 必须走 PT_LOAD(off,va)：ISO = base + off + (VA − va)。
    #   （base 是 ELF 头偏移，不是 VA 基址；两者差第一个 PT_LOAD 的 off，典型 0x80。）
    h0 = rd(base, 0x40)
    _phoff = struct.unpack_from('<I', h0, 0x1C)[0]
    _phes = struct.unpack_from('<H', h0, 0x2A)[0]
    _pt, _poff, _pva = struct.unpack('<3I', rd(base + _phoff, 12))
    VA_ISO_DELTA = base + _poff - _pva            # 对合法 PT_LOAD 恒为 −0x6C780

    def iso_of(va):
        return VA_ISO_DELTA + va

    def rdva(va, n):
        return rd(iso_of(va), n)

    def word(va):
        return struct.unpack('<I', rdva(va, 4))[0]

    h = rd(base, 0x40)
    phoff = struct.unpack_from('<I', h, 0x1C)[0]
    phentsize = struct.unpack_from('<H', h, 0x2A)[0]
    phnum = struct.unpack_from('<H', h, 0x2C)[0]
    entry = struct.unpack_from('<I', h, 0x18)[0]
    if mode == 'hdr':
        print('iso      = %s' % iso)
        print('ELF@ISO  = 0x%07X（提示上界 0x%X，差 %d B）  magic=%s'
              % (base, hint, hint - base, h[:4]))
        print('entry    = 0x%08X  phoff=0x%X phentsize=%d phnum=%d'
              % (entry, phoff, phentsize, phnum))
        print('★ VA→ISO  = VA + (%d) = VA − 0x%X   （由第一个 PT_LOAD 推出）'
              % (VA_ISO_DELTA, -VA_ISO_DELTA))
        for i in range(phnum):
            t, off, va, pa, fs, ms, fl, al = struct.unpack(
                '<8I', rd(base + phoff + i * phentsize, 32))
            print('  PT type=%d off=0x%07X va=0x%08X filesz=0x%07X memsz=0x%07X flags=0x%X'
                  % (t, off, va, fs, ms, fl))
        # 口径自检：ELF 头里的第一个 PT_LOAD 与「VA − 0x6C780」是否一致
        ok = (VA_ISO_DELTA == -ISO_OF_VA)
        print('  [口径自检] base(0x%X)+PT0.off(0x%X)−PT0.va(0x%X) = −0x%X ; 期望 −0x%X ⇒ %s'
              % (base, _poff, _pva, -VA_ISO_DELTA, ISO_OF_VA,
                 '一致 ✓' if ok else '不一致 ✗'))
    elif mode == 'word':
        for s in sys.argv[3:]:
            va = int(s, 16)
            w = word(va)
            print('VA 0x%08X (ISO 0x%07X) = 0x%08X  %s'
                  % (va, va - ISO_OF_VA, w, CD.dis(w, va)))
    elif mode == 'dis':
        lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
        for va in range(lo, hi, 4):
            w = word(va)
            print('  %08x  %08x  %-44s ; %s'
                  % (va, w, CD.dis(w, va), rdva(va, 4).hex()))
    else:
        raise SystemExit(__doc__)
    f.close()


if __name__ == '__main__':
    main()
