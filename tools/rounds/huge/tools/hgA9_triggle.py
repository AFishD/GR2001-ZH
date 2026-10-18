# -*- coding: utf-8 -*-
r"""hgA9_triggle.py — 只读: 反汇编 `SimHuman::TriggleForBlackCamera`（唯一确认调用
`GetFont(6)` = `huge` 面的函数），并解析它传给 DrawString 的字符串常量。

产出: work/builds/GR_HUGE/evidence/hgA9_triggle.txt
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        e, f = H.A.load_elf(tag)
        blob = e.b
        s = e.sym_at(0x3DEFA4)
        va0, sz = s['value'], s['size']
        W('=' * 100)
        W('%s  %s  VA 0x%X size=%d' % (tag, s['name'], va0, sz))
        # 收集 lui/addiu 立即数构造的地址, 指出落在哪个字符串符号上
        lui = {}
        strrefs = []
        for (a, w, t) in H.dis_range(blob, va0, sz // 4, H.VA2FILE):
            op = w >> 26
            rt = (w >> 16) & 0x1F
            rs = (w >> 21) & 0x1F
            if op == 0x0F:                       # lui
                lui[rt] = (w & 0xFFFF) << 16
            elif op in (0x09, 0x0D) and rs in lui:   # addiu/ori
                imm = w & 0xFFFF
                imm = imm - 0x10000 if (imm & 0x8000 and op == 0x09) else imm
                v = (lui[rs] + imm) & 0xFFFFFFFF
                if 0x500000 <= v < 0x600000:
                    strrefs.append((a, v))
            if op in (2, 3):
                pass
        strrefs = sorted(set(strrefs))
        W('  --- 落在 0x500000..0x600000 (字符串/常量区) 的 lui+addiu 构造: %d 处 ---' % len(strrefs))
        for (a, v) in strrefs:
            sym = e.sym_at(v)
            o = v - H.VA2FILE
            raw = blob[o:o + 64] if 0 <= o < len(blob) else b''
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in raw)
            W('    @%08X -> 0x%08X  %-24s  %r' % (a, v, (sym['name'] if sym else '?'), asc[:56]))
        W('')
        W('  --- 完整反汇编 ---')
        for (a, w, t) in H.dis_range(blob, va0, sz // 4, H.VA2FILE):
            W('   %08X  %08X  %s' % (a, w if w is not None else 0, t))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA9_triggle.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote hgA9_triggle.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
