# -*- coding: utf-8 -*-
r"""hgA8_fontidx.py — 只读(但重新反汇编): 判定每个 DrawString/GetFont 调用点的「字体索引」实参。

做法: 对每个调用点，从调用点往前线性回溯，遇控制流(j/jal/jr/branch)或函数入口即停，
      记录最后一条写 a3(或 a1) 的指令；`X,REG,zero` 形式的 R5900 寄存器搬移单独识别。

产出: work/builds/GR_HUGE/evidence/hgA8_fontidx.txt / .json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

R = H.A.R
WRITE_OPS = {0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi',
             0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui', 0x20: 'lb', 0x21: 'lh', 0x23: 'lw',
             0x24: 'lbu', 0x25: 'lhu', 0x27: 'lwu', 0x37: 'ld', 0x1E: 'lq'}
CTRL = set([2, 3, 4, 5, 6, 7, 1])


def is_move(w):
    """R5900 的 `X, Y, zero` 形式搬移 (0x1C/0x28 编码，见报告注释)"""
    return (w >> 26) == 0x1C and (w & 0x3F) == 0x28 and ((w >> 16) & 0x1F) == 0


def main():
    lines = []
    W = lines.append
    res = {}
    for tag in ('ZH113b',):
        e, f = H.A.load_elf(tag)
        blob = e.b
        # 全镜像扫描 json 里的引用点
        import io
        import re
        j = json.load(io.open(os.path.join(H.EVID, 'hgA6_xref.json'), encoding='utf-8'))
        def rdw(va):
            o = va - H.VA2FILE
            return None if (o < 0 or o + 4 > len(blob)) else int.from_bytes(blob[o:o + 4], 'little')

        for tgt in ('219E00', '3A17D0', '219A70', '219EB0'):
            argreg = 7 if tgt in ('219E00',) else (5 if tgt == '3A17D0' else 7)
            for h in j[tag][tgt]:
                va = h['va']
                s = e.sym_at(va)
                lo = s['value'] if s else va - 400
                found = None
                for k in range(1, 30):
                    a = va - 4 * k
                    if a < lo:
                        break
                    w = rdw(a)
                    if w is None:
                        break
                    op = w >> 26
                    if op in CTRL:
                        break
                    if ((w >> 16) & 0x1F) == argreg and (op in WRITE_OPS or is_move(w)):
                        found = (a, w, H.A.dis1(w, a) if not is_move(w)
                                 else 'mov %s,%s   [0x%08X]' % (R[(w >> 11) & 0x1F], R[(w >> 21) & 0x1F], w))
                        break
                idx = None
                if found and 'zero,' in found[2] and (',' in found[2]):
                    try:
                        idx = int(found[2].split(',')[-1])
                    except ValueError:
                        idx = None
                W('%s  @%08X  %s+0x%X' % ({'219E00': 'DrawString#2(fontIdx)',
                                            '3A17D0': 'GetFont(int)',
                                            '219A70': 'DrawString#3(RSFont*)',
                                            '219EB0': 'DrawString#1(RSFont*)'}[tgt],
                                           va, s['name'] if s else '?', va - s['value'] if s else 0))
                W('      %s     → fontIdx=%s' % (found[2] if found else '<未在直线块内找到>', idx))
                res.setdefault(tgt, []).append(dict(va=va, sym=s['name'] if s else '?',
                                                    setter=found[2] if found else None,
                                                    idx=idx))
        W('')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA8_fontidx.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    open(os.path.join(H.EVID, 'hgA8_fontidx.json'), 'w', encoding='utf-8').write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
