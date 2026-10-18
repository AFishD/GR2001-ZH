# -*- coding: utf-8 -*-
r"""reduce_check.py — 改写的**快速自查**器 (可用集口径 = 与 inject 预检一致)

用法:
  python reduce_check.py                 # 检查 new/ 下所有文件
  python reduce_check.py new/SFXML_T0043.txt [更多文件]
  python reduce_check.py --avail 她父历业狂    # 只回答「这些字在不在现役字库里?」
  python reduce_check.py --dump-charset  out.txt   # 把 1285 个现役字导出成可读清单

输出: 每个文件 → 超范围字 (含 U+码位与出现次数) / {WRAP} 写法与位置问题 / 与原文的长度差。
退出码: 0 = 全部干净; 1 = 还有超范围字或标记问题。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402

NEW = os.path.join(HERE, 'new')
OLD = os.path.join(HERE, 'old')
TGT = os.path.join(HERE, 'reduce_targets.json')


def load_new(path):
    """读一份改写稿。约定: 文件内容 = 单元格文本; 末尾的**一个**换行是编辑器/写文件带的,
    自动去掉 (原单元格不以换行结尾; 这条由 --check 与原文对照时复核)。"""
    t = io.open(path, encoding='utf-8', newline='').read()
    t = t.replace('\r\n', '\n')
    if t.endswith('\n'):
        t = t[:-1]
    return t


def main():
    args = sys.argv[1:]
    if args and args[0] == '--avail':
        miss = [c for c in ''.join(args[1:]) if not L.encodable(c)]
        print('查 %d 个字符: 可用 %d, **不可用 %d**'
              % (len(''.join(args[1:])), len(''.join(args[1:])) - len(miss), len(miss)))
        if miss:
            print('不可用: %s' % ' '.join('%s(U+%04X)' % (c, ord(c)) for c in miss))
        return 0
    if args and args[0] == '--dump-charset':
        out = args[1] if len(args) > 1 else os.path.join(HERE, 'available_charset.txt')
        chars = sorted(c for c in L.AVAIL if ord(c) >= 0x80)
        with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# 现役字库可用字 (charset_compiled_zh16.json 的 pair_of + codes)\n')
            f.write('# 共 %d 个汉字/符号; 另加 ASCII 0x20..0x7E 全部可打印字符\n' % len(chars))
            for i in range(0, len(chars), 50):
                f.write(''.join(chars[i:i + 50]) + '\n')
        print('→ %s (%d 字)' % (out, len(chars)))
        return 0

    targets = json.load(io.open(TGT, encoding='utf-8'))
    files = args or [os.path.join(NEW, f) for f in sorted(os.listdir(NEW))] \
        if os.path.isdir(NEW) else args
    files = [f for f in files if f.endswith('.txt')]
    bad = 0
    tot_kinds, tot_hits = set(), 0
    for p in files:
        rid = os.path.basename(p)[:-4].replace('_', ':', 1)
        new = load_new(p)
        miss = L.missing_of(new)
        hits = L.missing_count(new)
        wprobs = L.wrap_pos_problems(new)
        old = targets.get(rid, {}).get('text', '')
        flag = 'OK ' if not miss and not wprobs else '!! '
        if miss or wprobs:
            bad += 1
        print('%s%-14s %5d→%5d 字符  超范围 %2d 种 / %3d 次  %s'
              % (flag, rid, len(old), len(new), len(miss), hits,
                 '标记问题 %d' % len(wprobs) if wprobs else ''))
        if miss:
            print('     超范围字: %s' % ' '.join('%s(%d)' % (c, new.count(c)) for c in miss))
            tot_kinds |= set(miss)
            tot_hits += hits
        for (kind, pos, frag, why) in wprobs:
            print('     [%s] @%d %r: %s' % (kind, pos + 1, frag, why.split('——')[0].strip()))
    print('\n合计: %d 个文件仍有问题; 涉及 %d 种超范围字 / %d 次'
          % (bad, len(tot_kinds), tot_hits))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
