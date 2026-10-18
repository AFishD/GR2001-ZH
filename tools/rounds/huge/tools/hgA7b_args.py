# -*- coding: utf-8 -*-
r"""hgA7b_args.py — 只读: 解析 hgA7_callsites.txt，抽出每个调用点前 14 条指令里对
a3/a1 等实参寄存器的立即数装载，判定 DrawString(2nd overload) 的 fontIdx。

产出: work/builds/GR_HUGE/evidence/hgA7b_args.txt
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, '..', 'evidence', 'hgA7_callsites.txt'))
OUT = os.path.abspath(os.path.join(HERE, '..', 'evidence', 'hgA7b_args.txt'))


def main():
    blocks, blk, tag = [], None, '?'
    for ln in io.open(P, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if ln.startswith('##'):
            tag = ln[3:].strip()
        m = re.match(r'^(\S.*?)  @VA 0x([0-9A-F]+)\s+in (.+)$', ln)
        if m:
            if blk:
                blocks.append(blk)
            blk = dict(lbl=m.group(1).strip(), va=int(m.group(2), 16), fn=m.group(3).strip(),
                       tag=tag, ins=[])
            continue
        m2 = re.match(r'^\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+(.*?)(\s+<<<)?$', ln)
        if m2 and blk is not None:
            blk['ins'].append((int(m2.group(1), 16), m2.group(3).strip(), bool(m2.group(4))))
    if blk:
        blocks.append(blk)

    L = []
    W = L.append
    for b in blocks:
        if b['tag'] != 'ZH113b':
            continue
        W('%-34s @%08X  %s' % (b['lbl'], b['va'], b['fn']))
        for (a, t, mk) in b['ins']:
            if re.match(r'^(addiu|ori|addi|lui|lw|lb|lbu|lhu)\s+(a3|a1|a2|t0|t1|t2|s\d|v0|v1),', t):
                W('      %08X  %-34s%s' % (a, t, '   <<< 调用点' if mk else ''))
        W('')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
    print('wrote hgA7b_args.txt (%d lines, %d blocks)' % (len(L), len(blocks)))


if __name__ == '__main__':
    main()
