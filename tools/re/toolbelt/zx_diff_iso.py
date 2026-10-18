# -*- coding: utf-8 -*-
r"""zx_diff_iso.py — 两张 ISO 的**逐字节差异表** (分块哈希 + 段合并)

用法: python zx_diff_iso.py <A.iso> <B.iso> [--chunk 65536] [--max 80] [--out F]
输出: 差异区段 [start, end) 列表 + 每段字节数 + 与期望区域的对照 (MENU.IMG/ELF 站点)。
"""
import argparse
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MENU_LBA, SEC = 776286, 2048
MENU_OFF = MENU_LBA * SEC
ELF_SITES_ISO = [0x3AA768, 0x3AA9E0, 0x3AAD9C, 0x4F8F24]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--chunk', type=int, default=1 << 16)
    ap.add_argument('--max', type=int, default=80)
    ap.add_argument('--out', default=None)
    x = ap.parse_args()
    sa, sb = os.path.getsize(x.a), os.path.getsize(x.b)
    print('A = %s (%d B)' % (x.a, sa))
    print('B = %s (%d B)' % (x.b, sb))
    n = min(sa, sb)
    diff = []
    with open(x.a, 'rb') as fa, open(x.b, 'rb') as fb:
        off = 0
        while off < n:
            k = min(x.chunk, n - off)
            da, db = fa.read(k), fb.read(k)
            if da != db:
                # 细化到 4 KB
                for j in range(0, k, 4096):
                    pa, pb = da[j:j + 4096], db[j:j + 4096]
                    if pa != pb:
                        s = off + j
                        e = s + len(pa)
                        if diff and diff[-1][1] >= s:
                            diff[-1][1] = max(diff[-1][1], e)
                        else:
                            diff.append([s, e])
            off += k
    tot = sum(e - s for s, e in diff)
    print('★ 差异区段 %d 个, 合计 %d B (占 %.6f%%)' % (len(diff), tot, 100.0 * tot / max(1, n)))
    in_menu = sum(max(0, min(e, MENU_OFF + 58331136) - max(s, MENU_OFF))
                  for s, e in diff if e > MENU_OFF and s < MENU_OFF + 58331136)
    elf = [s for s in ELF_SITES_ISO if any(a <= s < b for a, b in diff)]
    print('  其中落在 MENU.IMG 区内 = %d B ; 落在 ELF 4 个 gate 站点所在区段 = %d/4'
          % (in_menu, len(elf)))
    lines = []
    for (s, e) in diff[:x.max]:
        tag = ''
        if s >= MENU_OFF:
            tag = ' [MENU.IMG +0x%X]' % (s - MENU_OFF)
        elif any(a - 4 <= s <= a + 4 for a in ELF_SITES_ISO):
            tag = ' [ELF gate]'
        lines.append('  0x%09X..0x%09X  %8d B%s' % (s, e, e - s, tag))
    print('\n'.join(lines))
    if len(diff) > x.max:
        print('  ... 还有 %d 段' % (len(diff) - x.max))
    if sa != sb:
        print('!! 尺寸不同 ⇒ 尾部差异 %d B' % abs(sa - sb))
    if x.out:
        with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('A=%s (%d B)\nB=%s (%d B)\n差异区段 %d 个, 合计 %d B\n'
                    % (x.a, sa, x.b, sb, len(diff), tot))
            for (s, e) in diff:
                f.write('0x%09X 0x%09X %d\n' % (s, e, e - s))
        print('→ %s' % x.out)


if __name__ == '__main__':
    main()
