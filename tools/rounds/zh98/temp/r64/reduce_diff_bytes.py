# -*- coding: utf-8 -*-
r"""reduce_diff_bytes.py — 找两个文件的**第一处字节差异** (诊断写盘口径)。只读。"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    a, b = sys.argv[1], sys.argv[2]
    A = open(a, 'rb').read()
    B = open(b, 'rb').read()
    print('%s: %d B' % (os.path.basename(a), len(A)))
    print('%s: %d B' % (os.path.basename(b), len(B)))
    n = min(len(A), len(B))
    for i in range(n):
        if A[i] != B[i]:
            print('首处差异 @%d' % i)
            print('  A: %r' % A[max(0, i - 40):i + 40])
            print('  B: %r' % B[max(0, i - 40):i + 40])
            print('  A 里 \\r 总数 %d, B 里 %d' % (A.count(b'\r'), B.count(b'\r')))
            print('  A 里 \\n 总数 %d, B 里 %d' % (A.count(b'\n'), B.count(b'\n')))
            return
    print('前 %d 字节相同; 长度差 %d' % (n, len(A) - len(B)))


if __name__ == '__main__':
    main()
