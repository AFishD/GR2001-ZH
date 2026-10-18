# -*- coding: utf-8 -*-
r"""ab5b_immrange.py — 立即数「区间」引用扫描 (只读): 补 C.3 的漏网

不只匹配精确地址, 而是匹配任何 `lui+addiu/ori` 构造出的值落在这些区间内:
  · cave 代码区      0x407000..0x407100 / 0x408900..0x408A00 / 0x411600..0x411700
                     0x416E00..0x417800 / 0x565600..0x565B00
  · loading 字符串区 0x577F00..0x578200
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANGES = [(0x407000, 0x407100, 'strlwr 覆盖区'),
          (0x408900, 0x408A00, 'strupr 覆盖区'),
          (0x411600, 0x411700, 'sceIpuInit cave'),
          (0x416E00, 0x417800, 'sce* cave 群'),
          (0x565600, 0x565B00, 's_Pool cave 群'),
          (0x577F00, 0x578200, 'loading 字符串区')]


def scan(e):
    ph = [p for p in e.phdrs if p['type'] == 1 and p['filesz'] > 0][0]
    o0, o1 = ph['off'], ph['off'] + ph['filesz']
    hits = []
    for o in range(o0 & ~3, o1 - 3, 4):
        w = __import__('struct').unpack_from('<I', e.b, o)[0]
        if (w >> 26) != 0x0F:
            continue
        rt = (w >> 16) & 0x1F
        hi = w & 0xFFFF
        for k in (1, 2, 3):
            o2 = o + 4 * k
            if o2 + 4 > o1:
                break
            w2 = __import__('struct').unpack_from('<I', e.b, o2)[0]
            op2 = w2 >> 26
            if op2 not in (0x09, 0x0D):
                continue
            if ((w2 >> 21) & 0x1F) != rt or ((w2 >> 16) & 0x1F) != rt:
                continue
            lo = w2 & 0xFFFF
            val = ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF \
                if op2 == 0x09 else ((hi << 16) | lo)
            for (a, b, nm) in RANGES:
                if a <= val < b:
                    va = e.off2va(o)[0]
                    s = e.sym_at(va)
                    hits.append((va, val, nm, 'lui/addiu' if op2 == 0x09 else 'lui/ori',
                                 s['name'] if s else '?', va - s['value'] if s else 0))
    return hits


def main():
    for tag in ('EN_ORIG', 'ZH113b'):
        e, _ = A.load_elf(tag)
        h = scan(e)
        print('== %s: 命中 %d 处' % (tag, len(h)))
        for (va, val, nm, kind, sn, dl) in h:
            print('   0x%08X → 0x%08X  [%s]  %s  in %s+0x%X' % (va, val, nm, kind, sn, dl))
    print('\n注: EN 的 "命中" 若指向同一区间即说明原盘确有代码引用该区（可能是真代码/真字符串）。')


if __name__ == '__main__':
    main()
