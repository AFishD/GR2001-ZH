# -*- coding: utf-8 -*-
r"""reduce_expand.py — 把 reduce_targets.json 里的 27 条原文展开成 old/<id>.txt (带换行)

只读 JSON, 只写 r64/old/。目的是让「改写的输入」用编辑器看得清 (JSON 里的 \n 看不清)。
输出文件 = **单元格原文逐字符照抄**, 末尾不加换行 (用 --verify 复核)。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    src = os.path.join(HERE, 'reduce_targets.json')
    d = json.load(io.open(src, encoding='utf-8'))
    out = os.path.join(HERE, 'old')
    os.makedirs(out, exist_ok=True)
    for rid, e in sorted(d.items()):
        t = e['text']
        p = os.path.join(out, rid.replace(':', '_') + '.txt')
        io.open(p, 'w', encoding='utf-8', newline='').write(t)
        en = e.get('en') or ''
        if en:
            io.open(os.path.join(out, rid.replace(':', '_') + '.en.txt'),
                    'w', encoding='utf-8', newline='').write(en)
        zh = e.get('zh') or ''
        if zh:
            io.open(os.path.join(out, rid.replace(':', '_') + '.zh.txt'),
                    'w', encoding='utf-8', newline='').write(zh)
        print('%-14s %5d 字符  %3d 种缺字 %4d 次  → %s'
              % (rid, len(t), e['n_missing'], e['n_missing_hits'], os.path.basename(p)))
    print('→ %s' % out)


if __name__ == '__main__':
    main()
