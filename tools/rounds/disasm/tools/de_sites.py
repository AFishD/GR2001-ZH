# -*- coding: utf-8 -*-
r"""de_sites.py —— 从 dediff JSON 汇总「原盘 ELF vs 汉化 ELF」的改动站点，并按区域分类。

只读。输出紧凑的站点表（VA / 字节数 / 原指令 / 新指令），便于逐条判定。
用法：
  python de_sites.py <diff.json> [--csv out.csv] [--region LO HI ...]
"""
import json
import sys

CAVES = [(0x415800, 0x418200), (0x565600, 0x565C00)]
TEXT_BLOB = (0x577000, 0x580000)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    j = json.load(open(sys.argv[1], encoding='utf-8'))
    runs = j['runs']
    print('# %s' % j['a'])
    print('# %s' % j['b'])
    print('# segs = %s' % (j.get('segs_a'),))
    print()
    in_cave, in_blob, other = [], [], []
    for r in runs:
        va = r['va']
        if any(lo <= va < hi for lo, hi in CAVES):
            in_cave.append(r)
        elif any(lo <= va < hi for lo, hi in [TEXT_BLOB]):
            in_blob.append(r)
        else:
            other.append(r)
    print('## A. 代码 cave 区（0x415800-0x418200 / 0x565600-0x565C00）：%d run' % len(in_cave))
    print('## B. 文本/数据区（>=0x577000）：%d run' % len(in_blob))
    print('## C. 其它（原函数体被改写 / 钩子 / 常量）：%d run' % len(other))
    print()
    # 把 C 段按地址聚成"族"（相邻 < 0x400 归一族）
    other.sort(key=lambda r: r['va'])
    fams = []
    for r in other:
        if fams and r['va'] - fams[-1][-1]['va'] <= 0x400:
            fams[-1].append(r)
        else:
            fams.append([r])
    print('### C 段聚成 %d 族：' % len(fams))
    for f in fams:
        lo = f[0]['va']
        hi = f[-1]['va']
        nb = sum(r['len'] for r in f)
        print()
        print('--- 族 @ 0x%08X..0x%08X  (%d run / %d B) ---' % (lo, hi, len(f), nb))
        for r in f:
            print('  0x%08X  %2dB  A=`%s`  B=`%s`' % (r['va'], r['len'], r['a_dis'], r['b_dis']))


if __name__ == '__main__':
    main()
