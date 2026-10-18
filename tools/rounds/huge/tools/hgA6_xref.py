# -*- coding: utf-8 -*-
r"""hgA6_xref.py — 只读: 找 RSFontMgr::DrawString 三个重载 / GetFont / Get() 的全部引用点，
并对每个 `jal 0x219E00`（第 5 参数 = int fontIndex 的那个重载）回溯 a3 的取值。

口径:
  a3 (r7) 在调用点前若干条指令内由 `addiu a3,zero,IMM` / `ori a3,zero,IMM` / `addiu a3,REG,IMM`
  或 `lw a3,...` 设定。这里把最近一次写 a3 的指令记下来。
产出: work/builds/GR_HUGE/evidence/hgA6_xref.txt / .json
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

TARGETS = {
    0x219A70: 'DrawString(f,..,RSFont* ,..)  [3rd overload]',
    0x219E00: 'DrawString(f,..,int fontIdx,..) [2nd overload]  ★ face 由 fontIdx 决定',
    0x219EB0: 'DrawString(i,..,RSFont* ,..)  [1st overload]',
    0x3A17D0: 'RSFontMgr::GetFont(int)',
    0x3A17E0: 'RSFontMgr::Get()',
    0x219380: 'RSFontMgr::ReadResourceFile(char const*)',
}

WRITES = {0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi',
          0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
          0x21: 'lh', 0x20: 'lb', 0x37: 'ld'}


def scan(blob, lo, hi):
    """扫 [lo,hi) 区间，返回全部指令 (va, word)"""
    out = []
    for a in range(lo, hi, 4):
        o = a - H.VA2FILE
        if 0 <= o and o + 4 <= len(blob):
            out.append((a, struct.unpack_from('<I', blob, o)[0]))
    return out


def main():
    lines = []
    W = lines.append
    res = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        blob = e.b
        # 全镜像线性扫一遍（只扫有文件的 PH）
        ins = []
        for p in e.phdrs:
            if p['type'] != 1:
                continue
            ins += scan(blob, p['vaddr'], p['vaddr'] + p['filesz'])
        ins.sort()
        idx = {a: i for i, (a, w) in enumerate(ins)}
        W('=' * 110)
        W('%s  指令总数 %d' % (tag, len(ins)))
        for tgt in TARGETS:
            hits = []
            for i, (a, w) in enumerate(ins):
                op = w >> 26
                if op in (2, 3):
                    if ((w & 0x3FFFFFF) << 2) == tgt:
                        hits.append((a, 'j' if op == 2 else 'jal', w))
            W('--- %s  0x%X  引用 %d ---' % (TARGETS[tgt], tgt, len(hits)))
            for (a, kind, w) in hits:
                s = e.sym_at(a)
                where = ('%s+0x%X' % (s['name'], a - s['value'])) if s else '?'
                extra = ''
                if tgt == 0x219E00:
                    # 回溯 a3 的最近写
                    j = idx[a]
                    found = None
                    for k in range(j - 1, max(0, j - 40), -1):
                        aw, ww = ins[k]
                        if (ww >> 26) == 3 or (ww >> 26) == 2:
                            continue                    # 跳过其它 jal/j
                        if (ww >> 26) == 1 and ((ww >> 16) & 0x1F) == 7:
                            pass
                        if ((ww >> 16) & 0x1F) == 7 and (ww >> 26) in WRITES:
                            found = (aw, ww, H.A.dis1(ww, aw))
                            break
                    extra = ('  a3<- %s' % found[2]) if found else '  a3<- ?'
                W('    %08X  %-4s  %s%s' % (a, kind, where, extra))
                W('        %s' % H.A.dis1(w, a))
            res.setdefault(tag, {})['%X' % tgt] = [
                dict(va=a, kind=kind, sym=('%s+0x%X' % (e.sym_at(a)['name'], a - e.sym_at(a)['value']))
                     if e.sym_at(a) else '?') for (a, kind, w) in hits]
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA6_xref.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    open(os.path.join(H.EVID, 'hgA6_xref.json'), 'w', encoding='utf-8').write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print('wrote hgA6_xref.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
