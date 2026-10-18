# -*- coding: utf-8 -*-
r"""reduce_ctx.py — 打印**超范围字**在 27 条文案里的实际上下文 (改写决策用)

用法:
  python reduce_ctx.py                 # 按出现次数降序, 每个字最多 3 条上下文
  python reduce_ctx.py 她 父 女 历     # 只看这些字 (不限条数)
  python reduce_ctx.py --all --max 2   # 全部超范围字, 每个最多 2 条
只读 old/, 不写盘。
"""
import io
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402

TGT = os.path.join(HERE, 'reduce_targets.json')


def main():
    args = [a for a in sys.argv[1:]]
    maxn = 3
    if '--max' in args:
        i = args.index('--max')
        maxn = int(args[i + 1])
        del args[i:i + 2]
    d = json.load(io.open(TGT, encoding='utf-8'))
    cnt, ctx = Counter(), defaultdict(list)
    for rid, e in sorted(d.items()):
        t = e['text']
        for ch in set(L.missing_of(t)):
            n = t.count(ch)
            cnt[ch] += n
            for m in range(len(t)):
                if t[m] != ch:
                    continue
                a, b = max(0, m - 14), min(len(t), m + 15)
                s = t[a:b].replace('\n', '⏎')
                ctx[ch].append('%s: …%s…' % (rid, s))
                if len(ctx[ch]) >= (maxn if not args else 99):
                    break
    want = args or [c for c, _ in cnt.most_common()]
    for ch in want:
        if ch not in cnt:
            continue
        print('=== %s (U+%04X) ×%d  [%d 条]' % (ch, ord(ch), cnt[ch], len(ctx[ch])))
        for c in ctx[ch][:maxn if not args else 99]:
            print('   %s' % c)


if __name__ == '__main__':
    main()
