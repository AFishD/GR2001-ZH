# -*- coding: utf-8 -*-
r"""f364_diffq.py -- 全盘差异的**粗粒度**定位（4 MiB 块），避免刷屏"""
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OLD = r'work\builds\GR_ZH124\GR_ZH124.iso'
NEW = r'work\builds\GR_F364\GR_F364.iso'
BLK = 1 << 22


def main():
    so, sn = os.path.getsize(OLD), os.path.getsize(NEW)
    print('old %d new %d same_size %s' % (so, sn, so == sn))
    bad = []
    with open(OLD, 'rb') as fa, open(NEW, 'rb') as fb:
        i = 0
        while True:
            a, b = fa.read(BLK), fb.read(BLK)
            if not a:
                break
            if a != b:
                # 块内细化
                sub = []
                for k in range(0, len(a), 1 << 16):
                    x, y = a[k:k + (1 << 16)], b[k:k + (1 << 16)]
                    if x != y:
                        sub.append((i * BLK + k, sum(1 for j in range(len(x)) if x[j] != y[j])))
                bad.append((i, sub))
            i += 1
    print('不同的 %d MiB 块数 = %d / %d' % (BLK >> 20, len(bad), i))
    tot = 0
    for (bi, sub) in bad:
        n = sum(c for _o, c in sub)
        tot += n
        print('  块 %3d  @ISO 0x%09X .. 0x%09X : 不同 %d B ; 64KiB 子块 %d 个 %s'
              % (bi, bi * BLK, (bi + 1) * BLK, n, len(sub),
                 ['0x%X' % o for o, _c in sub[:6]]))
    print('全盘不同字节总计 = %d' % tot)
    return 0


if __name__ == '__main__':
    sys.exit(main())
